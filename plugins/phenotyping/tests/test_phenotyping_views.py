"""Tests for the phenotyping view validator and its example seam schemas."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pyarrow as pa
import pyarrow.parquet as pq

PLUGIN = Path(__file__).resolve().parents[1]
FLOAT_MAX = 1.7976931348623157e308


def load_script(relative: str, name: str) -> ModuleType:
    """Import a skill script by path (scripts are not a package)."""

    path = PLUGIN / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validate_views = load_script(
    "skills/phenotyping-onboarding-checks/scripts/validate_views.py",
    "phenotyping_validate_views",
)


def _design(**overrides: object) -> pa.Table:
    columns = {
        "unit_id": ["u1", "u2", "u3"],
        "genotype": ["g1", "g2", "g1"],
        "treatment": ["C", "T", "C"],
        "treatment_value": pa.array([None, None, None], pa.float64()),
        "replicate": ["1", "1", "2"],
    }
    columns.update(overrides)  # type: ignore[arg-type]
    return pa.table(columns)


def _observations(values: list[float | None] | None = None) -> pa.Table:
    return pa.table(
        {
            "unit_id": ["u1", "u1", "u2"],
            "time": [
                "2000-01-01T06:00:00",
                "2000-01-02T06:00:00",
                "2000-01-01T06:00:00",
            ],
            "trait": ["projected_area"] * 3,
            "method": ["cam/mask-a"] * 3,
            "scale": ["px"] * 3,
            "value": pa.array(values or [10.0, None, 12.0], pa.float64()),
        }
    )


def test_valid_views_pass(tmp_path: Path) -> None:
    pq.write_table(_design(), tmp_path / "design.parquet")
    pq.write_table(_observations(), tmp_path / "observations_cam.parquet")

    assert (
        validate_views.main(
            [
                str(tmp_path / "design.parquet"),
                str(tmp_path / "observations_cam.parquet"),
            ]
        )
        == 0
    )


def test_invalid_views_fail_with_reasons() -> None:
    schema = validate_views.load_schema("design")
    dup = validate_views.validate_table(_design(unit_id=["u1", "u1", "u3"]), schema)
    assert any("primary key" in e for e in dup["errors"])

    as_text = validate_views.validate_table(_design(treatment_value=["0", "50", "0"]), schema)
    assert any("treatment_value" in e for e in as_text["errors"])

    missing = validate_views.validate_table(pa.table({"genotype": ["g1"]}), schema)
    assert any("missing required columns" in e for e in missing["errors"])

    observations = validate_views.load_schema("observations")
    sentinel = validate_views.validate_table(_observations([10.0, FLOAT_MAX, 12.0]), observations)
    assert any("sentinel" in e for e in sentinel["errors"])

    bad_time = _observations().set_column(
        1, "time", pa.array(["yesterday", "2000-01-02", "2000-01-01"])
    )
    assert any(
        "ISO 8601" in e for e in validate_views.validate_table(bad_time, observations)["errors"]
    )


def test_every_seam_schema_is_valid_json_schema() -> None:
    import jsonschema

    for kind in validate_views.KINDS:
        schema = validate_views.load_schema(kind)
        jsonschema.Draft202012Validator.check_schema(schema)
        assert set(schema["x-primary-key"]) <= set(schema["properties"])
        assert set(schema["required"]) <= set(schema["properties"])
