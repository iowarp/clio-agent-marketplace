"""Shared fixtures: a small synthetic export bundle with planted traps.

Everything here is invented for the tests. The bundle mimics the *shape* of a
self-describing phenotyping export (manifest, docs, per-modality tables, an
asset directory) and plants one instance of each trap the onboarding scripts
must catch: a float-max sentinel, string-typed ghost columns whose names
differ from real ones by rounding, missing rows the flags do not mark, a flag
on every row, a declared row count that does not match, duplicate design
columns, and a key column whose format differs between tables.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
import pytest

PACK = Path(__file__).resolve().parents[1]
FLOAT_MAX = 1.7976931348623157e308
PLANTS = list(range(101, 113))  # 12 synthetic units
ROUNDS = [7, 8, 9]


def load_script(relative: str, name: str) -> ModuleType:
    """Import a pack script by path (scripts are not a package)."""

    path = PACK / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def tree_hash(root: Path) -> dict[str, str]:
    """SHA-256 of every file under root (to prove inputs are untouched)."""

    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _features() -> pa.Table:
    keys, plants, rounds, area, coverage, flags, score, note = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )
    for r in ROUNDS:
        for i, p in enumerate(PLANTS):
            keys.append(f"e1__{p}__{r}__cam")
            plants.append(p)
            rounds.append(r)
            empty = (i + r) % 5 == 0  # some rows have no plant in the mask
            area.append(None if empty else float(100 + 10 * i + 5 * r))
            coverage.append(0.0 if empty else float(20 + i))
            row_flags = ["low_mask_coverage"]  # universal flag
            if empty and i % 2 == 0:
                row_flags.append("empty_mask")  # flags only some empty rows
            flags.append(row_flags)
            score.append(FLOAT_MAX if i == 3 else float(i) / 10)  # planted sentinel
            note.append("")  # ghost string column
    return pa.table(
        {
            "sample_key": keys,
            "plant_id": pa.array(plants, pa.int64()),
            "round_id": pa.array(rounds, pa.int64()),
            "area_px": pa.array(area, pa.float64()),
            "mask_coverage_pct": pa.array(coverage, pa.float64()),
            "qc_flags": pa.array(flags, pa.list_(pa.string())),
            "score": pa.array(score, pa.float64()),
            "operator_note": pa.array(note, pa.string()),
            "experiment_id": pa.array([1] * len(keys), pa.int64()),
        }
    )


def _design() -> pa.Table:
    genotypes = ["g1", "g2", "g3"]
    doses = [0, 50]
    rows = {
        "plant_id": [],
        "genotype": [],
        "treatment": [],
        "design_treatment": [],
        "replicate": [],
    }
    for i, p in enumerate(PLANTS):
        rows["plant_id"].append(p)
        rows["genotype"].append(genotypes[i % 3])
        rows["treatment"].append(doses[(i // 3) % 2])
        rows["design_treatment"].append(doses[(i // 3) % 2])
        rows["replicate"].append(i // 6 + 1)
    return pa.table(rows)


def _signatures() -> pa.Table:
    keys, plants, rounds = [], [], []
    for r in ROUNDS:
        for p in PLANTS:
            keys.append(f"e1__{p}__{r}__SPEC")
            plants.append(p)
            rounds.append(r)
    n = len(keys)
    return pa.table(
        {
            "sample_key": keys,
            "plant_id": pa.array(plants, pa.int64()),
            "round_id": pa.array(rounds, pa.int64()),
            "band_001_400p00nm": pa.array(
                [0.05 + 0.001 * k for k in range(n)], pa.float64()
            ),
            "band_001_400p01nm": pa.array([""] * n, pa.string()),
            "band_002_401p15nm": pa.array(
                [0.06 + 0.001 * k for k in range(n)], pa.float64()
            ),
            "band_002_401p16nm": pa.array([None] * n, pa.string()),
        }
    )


def build_bundle(root: Path) -> Path:
    """Write the synthetic bundle under ``root`` and return it."""

    root.mkdir(parents=True, exist_ok=True)
    cam = root / "cam"
    spec = root / "spec"
    images = cam / "cam-images"
    for directory in (cam, spec, images, root / "docs" / "modalities"):
        directory.mkdir(parents=True, exist_ok=True)
    features, design, signatures = _features(), _design(), _signatures()
    pq.write_table(features, cam / "cam-features.parquet")
    pacsv.write_csv(
        features.set_column(
            5,
            "qc_flags",
            pa.array([repr(v) for v in features.column("qc_flags").to_pylist()]),
        ),
        cam / "cam-features.csv",
    )
    pq.write_table(design, cam / "cam-design.parquet")
    pq.write_table(signatures, spec / "spec-signatures.parquet")
    for index in range(60):
        (images / f"img_{index:03d}.jpg").write_bytes(b"\xff\xd8\xff" + bytes([index]))
    manifest = {
        "export_version": 6,
        "generated_at": "synthetic",
        "experiment": {"id": "e1"},
        "modalities": [
            {
                "modality_id": "cam",
                "files": {
                    "features": "cam/cam-features.parquet",
                    "design": "cam/cam-design.parquet",
                },
                "row_counts": {
                    "features": features.num_rows,
                    "design": design.num_rows,
                },
                "asset_dirs": ["cam/cam-images"],
            },
            {
                "modality_id": "spec",
                "files": {"signatures": "spec/spec-signatures.parquet"},
                "row_counts": {
                    "signatures": signatures.num_rows + 1
                },  # planted mismatch
            },
        ],
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (root / "README.md").write_text(
        "# Synthetic export\n\nexport_version: 6\n\nColumns: area_px, score.\n",
        encoding="utf-8",
    )
    (root / "docs" / "modalities" / "cam.md").write_text(
        "# cam\n\n`area_px` is projected area in pixels.\n", encoding="utf-8"
    )
    (root / "docs" / "modalities" / "spec.md").write_text(
        "# spec\n\nReflectance bands.\n", encoding="utf-8"
    )
    return root


@pytest.fixture()
def bundle(tmp_path: Path) -> Path:
    """A fresh synthetic bundle per test."""

    return build_bundle(tmp_path / "bundle")
