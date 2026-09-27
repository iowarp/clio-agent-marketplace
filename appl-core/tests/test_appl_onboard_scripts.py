"""Functional tests for the onboard-dataset scripts on a synthetic bundle.

Run (CI form, see .github/workflows/ci.yml)::

    uv run --prerelease=allow --with "clio-agent @ git+https://github.com/iowarp/clio-agent@develop" \\
        --with "numpy>=1.24" --with "jsonschema>=4.18" --with trimesh --with pytest pytest appl-core/tests
"""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from conftest import FLOAT_MAX, load_script, tree_hash

SCRIPTS = "skills/onboard-dataset/scripts"
inventory = load_script(f"{SCRIPTS}/inventory.py", "appl_inventory")
audit_columns = load_script(f"{SCRIPTS}/audit_columns.py", "appl_audit_columns")
join_keys = load_script(f"{SCRIPTS}/join_keys.py", "appl_join_keys")
flag_check = load_script(f"{SCRIPTS}/flag_check.py", "appl_flag_check")
card = load_script(f"{SCRIPTS}/card.py", "appl_card")


def test_inventory_compares_declared_counts_and_finds_twins(bundle: Path) -> None:
    report = inventory.inventory(bundle)

    manifest = report["manifest"]
    assert manifest["identity"]["export_version"] == 6
    statuses = {c["path"]: c["status"] for c in manifest["declared_counts"]}
    assert statuses == {
        "cam/cam-features.parquet": "match",
        "cam/cam-design.parquet": "match",
        "spec/spec-signatures.parquet": "mismatch",
    }
    tables = {t["path"]: t for t in report["tables"]}
    assert tables["cam/cam-features.parquet"]["rows"] == 36
    assert tables["cam/cam-features.parquet"]["twins"] == ["cam/cam-features.csv"]
    assert "area_px" in tables["cam/cam-features.csv"]["header"]
    assert manifest["referenced_missing"] == []
    assert {d["path"] for d in report["docs"]} >= {
        "README.md",
        "docs/modalities/cam.md",
    }
    images = next(d for d in report["directories"] if d["path"] == "cam/cam-images")
    assert images["files"] == 60


def test_inventory_skips_agent_dir_and_reports_card(bundle: Path) -> None:
    (bundle / ".clio" / "views").mkdir(parents=True)
    pq.write_table(pa.table({"x": [1]}), bundle / ".clio" / "views" / "design.parquet")
    (bundle / ".clio" / "experiment-card.md").write_text("---\n---\n", encoding="utf-8")

    report = inventory.inventory(bundle)

    assert not any(t["path"].startswith(".clio") for t in report["tables"])
    assert report["agent_dir"] == {"path": ".clio", "exists": True, "card_exists": True}


def test_audit_finds_sentinel_ghosts_near_duplicates_and_twins(bundle: Path) -> None:
    features = audit_columns.audit(
        pq.read_table(bundle / "cam" / "cam-features.parquet")
    )
    f = features["findings"]
    sentinel = next(item for item in f["sentinel_columns"] if item["name"] == "score")
    assert sentinel["candidates"][0]["values"][0]["value"] == FLOAT_MAX
    assert "operator_note" in f["ghost_string_columns"]
    assert "experiment_id" in f["constant_columns"]
    assert "qc_flags" in f["list_like_columns"]

    signatures = audit_columns.audit(
        pq.read_table(bundle / "spec" / "spec-signatures.parquet")
    )
    s = signatures["findings"]
    assert set(s["all_empty_columns"]) == {"band_001_400p01nm", "band_002_401p16nm"}
    pairs = {
        (p["a"], p["b"]): p
        for p in s["near_duplicate_names"]
        if p["kind"] == "rounding"
    }
    assert ("band_001_400p00nm", "band_001_400p01nm") in pairs
    assert pairs[("band_001_400p00nm", "band_001_400p01nm")]["b_empty"] is True
    assert ("band_002_401p15nm", "band_002_401p16nm") in pairs
    # 400.01 vs 401.15 are real neighbouring bands, not a rounding twin
    assert ("band_001_400p01nm", "band_002_401p15nm") not in pairs

    design = audit_columns.audit(pq.read_table(bundle / "cam" / "cam-design.parquet"))
    assert ["treatment", "design_treatment"] in design["findings"]["identical_columns"]


def test_audit_reads_csv_lists_and_empty_strings(bundle: Path) -> None:
    table = audit_columns.read_table(bundle / "cam" / "cam-features.csv")
    report = audit_columns.audit(table)

    assert "qc_flags" in report["findings"]["list_like_columns"]
    assert "operator_note" in report["findings"]["all_empty_columns"]


def test_audit_detects_zero_as_missing_and_codes() -> None:
    table = pa.table(
        {
            "weight": [0.0] + [150.0 + i for i in range(40)],
            "code": [-9999.0] * 3 + [1.0 + i for i in range(38)],
        }
    )
    report = audit_columns.audit(table)

    assert report["findings"]["zero_as_missing_candidates"] == ["weight"]
    codes = next(
        item
        for item in report["findings"]["sentinel_columns"]
        if item["name"] == "code"
    )
    assert {"kind": "code", "value": -9999.0, "count": 3} in codes["candidates"]


def test_join_keys_reports_case_mismatch_and_component_keys(bundle: Path) -> None:
    a = pq.read_table(bundle / "cam" / "cam-features.parquet")
    b = pq.read_table(bundle / "spec" / "spec-signatures.parquet")

    report = join_keys.compare(a, b, ["sample_key"])

    assert report["overlap"]["shared_distinct_keys"] == 0
    assert any("letter case differs" in w for w in report["warnings"])
    assert any("low overlap" in w for w in report["warnings"])
    trials = {t["normalisation"]: t for t in report["normalisation_trials"]}
    assert trials["first 3 token(s) (casefolded)"]["shared_distinct"] == 36
    alternatives = [c["column"] for c in report["alternative_keys"]]
    assert {"plant_id", "round_id"} <= set(alternatives)

    composite = join_keys.compare(a, b, ["plant_id", "round_id"])
    assert composite["overlap"]["a_rows_matched"] == 36
    assert composite["warnings"] == []


def test_join_keys_flags_type_mismatch() -> None:
    a = pa.table({"k": [1, 2, 3]})
    b = pa.table({"k": ["1", "2", "3"]})

    report = join_keys.compare(a, b, ["k"])

    assert any("type mismatch" in w for w in report["warnings"])


def test_flag_check_finds_universal_and_unflagged_missing(bundle: Path) -> None:
    table = pq.read_table(bundle / "cam" / "cam-features.parquet")

    report = flag_check.check(table, "qc_flags", ["area_px"])

    assert report["universal_flags"] == ["low_mask_coverage"]
    assert report["missing_signal_rows"] > 0
    assert report["missing_without_any_flag"] == 0  # every row has the universal flag
    assert 0 < report["missing_without_specific_flag"] < report["missing_signal_rows"]
    empty = next(row for row in report["flags"] if row["flag"] == "empty_mask")
    assert empty["precision"] == 1.0
    assert empty["recall"] < 1.0


def test_flag_check_parses_string_lists_and_zero_signal(bundle: Path) -> None:
    table = flag_check.read_table(bundle / "cam" / "cam-features.csv")

    report = flag_check.check(
        table, "qc_flags", ["mask_coverage_pct"], zero_is_missing=True
    )

    assert report["universal_flags"] == ["low_mask_coverage"]
    assert (
        report["missing_signal_rows"]
        == flag_check.check(
            pq.read_table(bundle / "cam" / "cam-features.parquet"),
            "qc_flags",
            ["area_px"],
        )["missing_signal_rows"]
    )
    assert flag_check.parse_flags("a; b") == frozenset({"a", "b"})
    assert flag_check.parse_flags('["x", "y"]') == frozenset({"x", "y"})
    assert flag_check.parse_flags("[]") == frozenset()


def test_card_lifecycle(bundle: Path) -> None:
    created = card.init(bundle)
    assert created["ok"] is True
    text = (bundle / ".clio" / "experiment-card.md").read_text(encoding="utf-8")
    meta = card.parse_frontmatter(text)
    assert meta["export_version"] == "6"
    assert meta["manifest_sha256"] == created["manifest_sha256"]
    for section in (
        "## Traps found",
        "## Open questions for data owners",
        "## Proposed lessons",
        "## Loader and views",
    ):
        assert section in text

    assert card.init(bundle)["ok"] is False  # never overwrite silently
    assert card.status(bundle)["state"] == "current"
    assert card.status(bundle)["hashes"] == "not_recorded"

    views = bundle / ".clio" / "views"
    views.mkdir()
    (bundle / ".clio" / "loader.py").write_text("print('load')\n", encoding="utf-8")
    pq.write_table(pa.table({"unit_id": ["a"]}), views / "design.parquet")
    card.record(bundle)
    assert card.status(bundle)["hashes"] == "match"
    assert card.main(["verify", str(bundle)]) == 0

    pq.write_table(pa.table({"unit_id": ["b"]}), views / "design.parquet")
    drift = card.status(bundle)
    assert drift["hashes"] == "drift"
    assert drift["drifted"] == [".clio/views/design.parquet"]
    assert card.main(["verify", str(bundle)]) == 1

    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    manifest["generated_at"] = "later"
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert card.status(bundle)["state"] == "stale"


def test_card_force_replaces(bundle: Path) -> None:
    card.init(bundle)
    (bundle / ".clio" / "experiment-card.md").write_text("old", encoding="utf-8")
    assert card.init(bundle, force=True)["ok"] is True
    assert "old" != (bundle / ".clio" / "experiment-card.md").read_text(
        encoding="utf-8"
    )


def test_cli_entry_points_never_modify_inputs(
    bundle: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = tree_hash(bundle)
    out = tmp_path / "reports"
    features = str(bundle / "cam" / "cam-features.parquet")
    signatures = str(bundle / "spec" / "spec-signatures.parquet")

    assert inventory.main([str(bundle), "--out", str(out / "inv.json")]) == 0
    assert audit_columns.main([features, "--out", str(out / "cols.json")]) == 0
    assert audit_columns.main([signatures, "--sample", "5"]) == 0
    assert (
        join_keys.main(
            [
                features,
                signatures,
                "--key-column",
                "sample_key",
                "--out",
                str(out / "join.json"),
            ]
        )
        == 0
    )
    assert (
        flag_check.main(
            [
                features,
                "--flags",
                "qc_flags",
                "--signal",
                "area_px",
                "--out",
                str(out / "flags.json"),
            ]
        )
        == 0
    )

    assert tree_hash(bundle) == before
    printed = capsys.readouterr().out
    assert "SENTINEL candidate: score" in printed
    assert "UNIVERSAL flags" in printed
    for name in ("inv.json", "cols.json", "join.json", "flags.json"):
        json.loads((out / name).read_text(encoding="utf-8"))  # strict JSON
