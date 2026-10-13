"""Tests for the eval tooling: variant maker and the behavioral grader."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest
from conftest import FLOAT_MAX, PACK, load_script, tree_hash

make_variants = load_script("evals/scripts/make_variants.py", "appl_make_variants")
evaluate = load_script("evals/scripts/evaluate_appl_core.py", "appl_evaluate")
CASES = json.loads((PACK / "evals" / "behavioral-cases.json").read_text(encoding="utf-8"))


def _args(variant: str, **extra: object) -> argparse.Namespace:
    argv = ["SRC", "OUT", "--variant", variant]
    namespace = make_variants.build_parser().parse_args(argv)
    for key, value in extra.items():
        setattr(namespace, key, value)
    return namespace


def _make(bundle: Path, out: Path, variant: str, **extra: object) -> dict:
    before = tree_hash(bundle)
    record = make_variants.make_variant(bundle, out, _args(variant, **extra))
    assert tree_hash(bundle) == before, "the source bundle must never change"
    assert not (out / "cam" / "cam-images").exists(), "asset directories are not copied"
    assert not (out / ".clio").exists()
    assert (out.parent / f"{out.name}.variant.json").is_file()
    assert "cam/cam-images" in record["skipped_asset_dirs"]
    return record


def test_export_v7_sets_version_and_renames_one_column(bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / "v7"
    record = _make(bundle, out, "export_v7")

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["export_version"] == 7
    assert "export_version: 7" in (out / "README.md").read_text(encoding="utf-8")
    ((old, new),) = record["mutation"]["renames"].items()
    assert new == f"alt_{old}"


def test_categorical_treatment_maps_doses_to_labels(bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / "cat"
    record = _make(bundle, out, "categorical_treatment")

    design = pq.read_table(out / "cam" / "cam-design.parquet")
    assert set(design.column("treatment").to_pylist()) == {"C", "Ni"}
    assert set(design.column("design_treatment").to_pylist()) == {"C", "Ni"}
    assert record["mutation"]["control_level"] == 0.0


def test_unbalanced_drops_units_everywhere_and_updates_counts(bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / "unb"
    record = _make(bundle, out, "unbalanced", drop_fraction=0.25)

    dropped = {int(u) for u in record["mutation"]["dropped_units"]}
    assert len(dropped) == 3
    for rel in (
        "cam/cam-features.parquet",
        "cam/cam-design.parquet",
        "spec/spec-signatures.parquet",
    ):
        plants = set(pq.read_table(out / rel).column("plant_id").to_pylist())
        assert not plants & dropped
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    cam = manifest["modalities"][0]
    assert (
        cam["row_counts"]["features"]
        == pq.read_metadata(out / "cam" / "cam-features.parquet").num_rows
    )
    csv_lines = (out / "cam" / "cam-features.csv").read_text(encoding="utf-8").strip().splitlines()
    assert len(csv_lines) - 1 == cam["row_counts"]["features"]


def test_unbalanced_keeps_an_empty_table_with_the_unit_column(bundle: Path, tmp_path: Path) -> None:
    # Real exports ship zero-row tables that still carry the unit column (e.g. an
    # empty issues table); an untyped empty mask used to crash the filter.
    import pyarrow as pa

    empty = pa.table(
        {
            "plant_id": pa.array([], type=pa.int64()),
            "note": pa.array([], type=pa.string()),
        }
    )
    pq.write_table(empty, bundle / "issues.parquet")
    out = tmp_path / "unb-empty"
    _make(bundle, out, "unbalanced", drop_fraction=0.25)
    assert pq.read_table(out / "issues.parquet").num_rows == 0


def test_drop_modality_removes_it(bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / "drop"
    record = _make(bundle, out, "drop_modality", modality="spec")

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert [m["modality_id"] for m in manifest["modalities"]] == ["cam"]
    assert not (out / "spec").exists()
    assert not (out / "docs" / "modalities" / "spec.md").exists()
    assert record["mutation"]["modality"] == "spec"


def test_rename_columns_is_consistent(bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / "ren"
    _make(bundle, out, "rename_columns", rename=["area_px=projected_px"])

    features = pq.read_table(out / "cam" / "cam-features.parquet")
    assert "projected_px" in features.column_names and "area_px" not in features.column_names
    assert (
        "projected_px"
        in (out / "cam" / "cam-features.csv").read_text(encoding="utf-8").splitlines()[0]
    )
    assert "`projected_px`" in (out / "docs" / "modalities" / "cam.md").read_text(encoding="utf-8")


def test_sentinel_moves_to_a_sentinel_free_table(bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / "sent"
    record = _make(bundle, out, "sentinel_elsewhere", fraction=0.1)

    mutation = record["mutation"]
    assert mutation["table"] == "spec/spec-signatures.parquet"  # features already holds one
    column = pq.read_table(out / mutation["table"]).column(mutation["column"])
    assert (
        pc.sum(pc.cast(pc.equal(column, FLOAT_MAX), "int64")).as_py() == mutation["injected"] >= 1
    )


def test_variant_refuses_to_write_into_the_source(bundle: Path, tmp_path: Path) -> None:
    with pytest.raises(make_variants.VariantError):
        make_variants.make_variant(bundle, bundle / "variant", _args("export_v7"))
    with pytest.raises(make_variants.VariantError):
        make_variants.make_variant(bundle, bundle, _args("export_v7"))
    unrelated = tmp_path / "not-a-variant"
    unrelated.mkdir()
    (unrelated / "keep.txt").write_text("x", encoding="utf-8")
    with pytest.raises(make_variants.VariantError):
        make_variants.make_variant(bundle, unrelated, _args("export_v7", force=True))
    assert (unrelated / "keep.txt").exists()


def test_variant_force_replaces_its_own_output(bundle: Path, tmp_path: Path) -> None:
    out = tmp_path / "v"
    make_variants.make_variant(bundle, out, _args("export_v7"))
    with pytest.raises(make_variants.VariantError):
        make_variants.make_variant(bundle, out, _args("export_v7"))
    make_variants.make_variant(bundle, out, _args("unbalanced", force=True))
    assert json.loads((out / "manifest.json").read_text(encoding="utf-8"))["export_version"] == 6


# ---------------------------------------------------------------- grader

CARD = """---
card_format: clio-experiment-card/1
manifest_sha256: abc
---

## Checked facts

- [checked] a (evidence: x)
- [stated] b (source: y)

## Traps found

<!-- - [trap:not-a-class] a comment is ignored -->
- [trap:sentinel-values] t.value -- float max -- nulled (evidence: audit)
- [trap:universal-flag] t.qc -- on every row -- ignored

## Open questions for data owners

- What is the treatment unit?
"""


def _trace(case_id: str, **overrides: object) -> dict:
    trace = {
        "case_id": case_id,
        "response": "The export has a sentinel and a universal flag; the loader handles both. " * 3,
        "actions": [
            {
                "name": "load_skill",
                "arguments": {"skill_id": "onboard-dataset"},
                "result": {},
            },
            {
                "name": "shell_bash",
                "arguments": {"command": "uv run python inventory.py B"},
                "result": {},
            },
            {
                "name": "shell_bash",
                "arguments": {"command": "uv run W/.clio/datasets/k/loader.py B"},
                "result": {},
            },
            {
                "name": "shell_bash",
                "arguments": {"command": "uv run python card.py verify B"},
                "result": {},
            },
        ],
        "tasks": [],
        "questions": [],
        "sessions": [],
        "bundle": {
            "card_text": CARD,
            "view_hash_runs": [{"v": "1"}, {"v": "1"}],
            "verify_exit_codes": [0],
            "files_written": [],
            "source_access": {"mode": "read_only", "verified": True, "receipt": "access-receipt"},
            "source_hashes_before": {"measurements.csv": "a" * 64},
            "source_hashes_after": {"measurements.csv": "a" * 64},
            "source_writes": [],
            "inspected_sources": ["measurements.csv"],
            "findings": [{"description": "Three measured rows", "evidence": ["measurements.csv"]}],
            "adaptations": [
                {"description": "Read actual columns directly", "evidence": ["measurements.csv"]}
            ],
        },
    }
    trace.update(overrides)
    return trace


def _case(**expect: object) -> dict:
    return {"id": "c", "expect": expect}


def test_grader_accepts_a_compliant_trace() -> None:
    case = _case(
        response={"nonempty": True, "min_words": 10, "terms_any": ["sentinel"]},
        actions={
            "required_skills": ["onboard-dataset"],
            "required_scripts": ["inventory.py"],
        },
        card={
            "exists": True,
            "required_trap_classes": ["sentinel-values"],
            "min_open_questions": 1,
        },
        loader={"deterministic": True, "verified": True},
    )
    assert evaluate.evaluate_case(case, _trace("c")) == []


def test_grader_accepts_natural_claims_without_status_tags() -> None:
    trace = _trace("c")
    trace["response"] = (
        "I checked the recorded measurements and found sentinel values in the signal column. "
        "The calculation and its input table are retained with the analysis."
    )
    trace["bundle"]["card_text"] = (
        "# Analysis notes\n\nI checked the signal column; sentinel values are present.\n"
        "The protocol describes the reported signal units, which still need calibration.\n"
    )
    assert evaluate.evaluate_case(_case(card={"exists": True}), trace) == []


def test_grader_rejects_unreadable_and_noncompliant_traces() -> None:
    assert evaluate.evaluate_case(_case(), {"case_id": "c"})  # missing keys

    reprofiled = evaluate.evaluate_case(_case(outcome={"no_reprofile": True}), _trace("c"))
    assert any("re-profiled" in f.message for f in reprofiled)

    drift = _trace(
        "c",
        bundle={
            "card_text": CARD,
            "view_hash_runs": [{"v": "1"}, {"v": "2"}],
            "verify_exit_codes": [1],
        },
    )
    messages = [
        f.message
        for f in evaluate.evaluate_case(
            _case(loader={"deterministic": True, "verified": True}), drift
        )
    ]
    assert any("different view hashes" in m for m in messages)
    assert any("verify never passed" in m for m in messages)

    missing_trap = evaluate.evaluate_case(
        _case(card={"exists": True, "required_trap_classes": ["ghost-columns"]}),
        _trace("c"),
    )
    assert any("[trap:ghost-columns]" in f.message for f in missing_trap)

    wrote_views = _trace(
        "c",
        bundle={
            "card_text": None,
            "view_hash_runs": [{"v": "1"}],
            "files_written": ["W/.clio/datasets/k/views/x"],
        },
    )
    assert evaluate.evaluate_case(_case(outcome={"no_views_written": True}), wrote_views)
    legacy_views = _trace(
        "c",
        bundle={"card_text": None, "files_written": ["B/.clio/views/x"]},
    )
    assert evaluate.evaluate_case(_case(outcome={"no_views_written": True}), legacy_views)

    no_rerun = _trace("c", actions=[{"name": "wait_agent_tasks", "arguments": {}, "result": {}}])
    assert evaluate.evaluate_case(_case(loader={"parent_reran_after_child": True}), no_rerun)
    rerun = _trace(
        "c",
        actions=[
            {"name": "wait_agent_tasks", "arguments": {}, "result": {}},
            {
                "name": "shell_bash",
                "arguments": {"command": "uv run W/.clio/datasets/k/loader.py B"},
                "result": {},
            },
        ],
    )
    assert evaluate.evaluate_case(_case(loader={"parent_reran_after_child": True}), rerun) == []

    asked = _trace(
        "c",
        questions=[
            {
                "id": "q",
                "status": "pending",
                "source": "orchestrator",
                "prompt": "What unit is the dose in?",
            }
        ],
    )
    assert (
        evaluate.evaluate_case(_case(question={"min_count": 1, "terms_any": ["dose"]}), asked) == []
    )
    assert evaluate.evaluate_case(_case(question={"min_count": 1}), _trace("c"))


def test_case_file_is_consistent_with_the_pack() -> None:
    assert evaluate.validate_cases(CASES) == []
    skills = {p.parent.name for p in (PACK / "skills").glob("*/SKILL.md")}
    variants = set(make_variants.VARIANTS)
    for case in CASES:
        assert "{bundle_root}" in case["user_message"], case["id"]
        bundle = case["bundle"]
        assert bundle == "primary" or bundle.removeprefix("variant:") in variants, case["id"]
        for skill in case.get("method_skills", []):
            assert skill in skills, (case["id"], skill)
    level1 = {
        p.parent.name
        for p in (PACK / "skills").glob("*/SKILL.md")
        if re.search(r"^- level:L1$", p.read_text(encoding="utf-8"), re.MULTILINE)
    }
    covered = {s for c in CASES for s in c.get("method_skills", [])}
    assert level1 <= covered, "one question per L1 skill"


@pytest.mark.parametrize("tool", ["parquet_read_slice_tool", "shell_bash"])
def test_current_onboarding_accepts_different_analysis_paths(tool: str) -> None:
    """Equivalent source-backed work needs no prescribed loader, card or views."""
    trace = _trace("first_contact_onboarding")
    trace["actions"] = [{"name": tool, "arguments": {}, "result": {}}]
    trace["response"] = (
        "I inspected the supplied measurements and their recorded identifiers. "
        "The quality flags do not account for every missing observation, and the "
        "available treatment labels do not establish physical dose units. I retained "
        "those labels, checked the actual group counts, and kept uncertain encodings "
        "explicit. The source was read through its verified read-only connection. "
        "No source repair, fixed loader or normalized view set was needed to report "
        "these findings and the questions that would change a treatment comparison."
    )
    trace["bundle"].update(card_text=None, view_hash_runs=[], verify_exit_codes=[])
    case = next(row for row in CASES if row["id"] == "first_contact_onboarding")
    assert evaluate.evaluate_case(case, trace) == []


@pytest.mark.parametrize("failure", ["changed", "restored_write", "unverified", "missing_hashes"])
def test_read_only_acceptance_rejects_missing_or_failed_preservation(failure: str) -> None:
    """A clean final checksum alone cannot hide a successful source write."""
    trace = _trace("c")
    if failure == "changed":
        trace["bundle"]["source_hashes_after"]["measurements.csv"] = "b" * 64
    elif failure == "restored_write":
        trace["bundle"]["source_writes"] = ["measurements.csv"]
    elif failure == "unverified":
        trace["bundle"]["source_access"]["verified"] = False
    else:
        trace["bundle"].pop("source_hashes_before")
    assert evaluate.evaluate_case(_case(source={"read_only": True, "unchanged": True}), trace)


def test_adaptation_requires_observed_evidence_not_just_a_claim() -> None:
    trace = _trace("adapt_export_v7")
    case = next(row for row in CASES if row["id"] == "adapt_export_v7")
    trace["response"] = (
        "The export version is 7; I inspected the actual columns and readable measurements "
        "and documented their limitations."
    )
    assert evaluate.evaluate_case(case, trace) == []
    trace["bundle"]["adaptations"][0]["evidence"] = ["unrecorded-source"]
    assert evaluate.evaluate_case(case, trace)


def test_cases_do_not_prescribe_onboarding_scripts_or_view_schemas() -> None:
    for case in CASES:
        assert "required_scripts" not in case["expect"].get("actions", {})
        assert case["expect"].get("outcome", {}).get("no_views_written") is not True
        if case["id"] != "loader_determinism":
            assert "loader" not in case["expect"]
