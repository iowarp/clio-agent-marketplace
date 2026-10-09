"""Tests for the geometry-to-glb converter and the phenotyping view validator."""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from conftest import FLOAT_MAX, load_script, tree_hash

to_glb = load_script("skills/geometry-to-glb/scripts/to_glb.py", "appl_to_glb")
validate_views = load_script(
    "skills/phenotyping-onboarding-checks/scripts/validate_views.py",
    "appl_validate_views",
)

VERTICES = "0 0 0\n1 0 0\n0 1 0\n0 0 1\n"
FACES = "0 1 2\n0 1 3\n0 2 3\n1 2 3\n"
COLORS = "255 0 0\n255 0 0\n0 255 0\n0 255 0\n"


def _geometry(tmp_path: Path, faces: str = FACES) -> tuple[Path, Path, Path]:
    v, f, c = (
        tmp_path / "m.vertices.txt",
        tmp_path / "m.faces.txt",
        tmp_path / "m.colors.txt",
    )
    v.write_text(VERTICES, encoding="utf-8")
    f.write_text(faces, encoding="utf-8")
    c.write_text(COLORS, encoding="utf-8")
    return v, f, c


def _accessor_values(path: Path, index: int) -> np.ndarray:
    data = path.read_bytes()
    json_len = struct.unpack_from("<I", data, 12)[0]
    gltf = to_glb.read_glb_json(path)
    bin_start = 20 + json_len + 8
    accessor = gltf["accessors"][index]
    view = gltf["bufferViews"][accessor["bufferView"]]
    dtype = "<f4" if accessor["componentType"] == 5126 else "<u4"
    width = {"SCALAR": 1, "VEC3": 3}[accessor["type"]]
    raw = np.frombuffer(
        data,
        dtype=dtype,
        count=accessor["count"] * width,
        offset=bin_start + view["byteOffset"],
    )
    return raw.reshape(accessor["count"], width) if width > 1 else raw


def test_mesh_triplet_becomes_a_viewport_glb_with_segment_field(tmp_path: Path) -> None:
    v, f, c = _geometry(tmp_path)
    before = tree_hash(tmp_path)
    out = tmp_path / "out" / "mesh.glb"

    assert (
        to_glb.main(
            [
                "mesh",
                "--vertices",
                str(v),
                "--faces",
                str(f),
                "--colors",
                str(c),
                "-o",
                str(out),
                "--units",
                "mm",
            ]
        )
        == 0
    )

    gltf = to_glb.read_glb_json(out)
    clio = gltf["scenes"][0]["extras"]["clio"]
    assert clio["contract"] == "clio.fea-mesh.v1"
    assert clio["topology"] == "surface"
    assert clio["units"] == {"length": "mm"}
    assert clio["counts"]["vertices"] == 4 and clio["counts"]["triangles"] == 4
    primitive = gltf["meshes"][0]["primitives"][0]
    assert primitive["mode"] == 4
    assert set(primitive["attributes"]) == {"POSITION", "_NODE", "COLOR_0"}
    (segment,) = clio["fields"]
    assert (
        segment["name"] == "SEGMENT"
        and segment["location"] == "node"
        and segment["count"] == 4
    )
    assert list(_accessor_values(out, segment["accessor"])) == [1.0, 1.0, 0.0, 0.0]
    assert clio["segments"]["palette_rgb255"] == [[0, 255, 0], [255, 0, 0]]
    assert _accessor_values(out, primitive["indices"]).tolist() == [
        0,
        1,
        2,
        0,
        1,
        3,
        0,
        2,
        3,
        1,
        2,
        3,
    ]
    assert (out.stat().st_size % 4) == 0
    before.pop("out/mesh.glb", None)
    assert {
        k: v for k, v in tree_hash(tmp_path).items() if not k.startswith("out/")
    } == before


def test_one_based_quads_are_detected_and_split(tmp_path: Path) -> None:
    v, f, _ = _geometry(tmp_path, faces="1 2 3 4\n")
    out = tmp_path / "quad.glb"

    assert (
        to_glb.main(["mesh", "--vertices", str(v), "--faces", str(f), "-o", str(out)])
        == 0
    )

    clio = to_glb.read_glb_json(out)["scenes"][0]["extras"]["clio"]
    assert clio["conversion"] == {"index_base_detected": 1, "quads_split": True}
    assert clio["counts"]["triangles"] == 2
    assert clio["fields"] == []


def test_bad_geometry_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    v, f, c = _geometry(tmp_path, faces="0 1 9\n")
    assert (
        to_glb.main(
            [
                "mesh",
                "--vertices",
                str(v),
                "--faces",
                str(f),
                "-o",
                str(tmp_path / "x.glb"),
            ]
        )
        == 2
    )
    assert "out of range" in capsys.readouterr().err
    c.write_text("1 2 3\n", encoding="utf-8")
    f.write_text(FACES, encoding="utf-8")
    assert (
        to_glb.main(
            [
                "mesh",
                "--vertices",
                str(v),
                "--faces",
                str(f),
                "--colors",
                str(c),
                "-o",
                str(tmp_path / "x.glb"),
            ]
        )
        == 2
    )


def test_points_are_refused_unless_allowed(tmp_path: Path) -> None:
    points = tmp_path / "cloud.points.txt"
    points.write_text(VERTICES, encoding="utf-8")
    assert to_glb.main(["points", str(points), "-o", str(tmp_path / "p.glb")]) == 3
    assert not (tmp_path / "p.glb").exists()

    assert (
        to_glb.main(
            ["points", str(points), "-o", str(tmp_path / "p.glb"), "--allow-points"]
        )
        == 0
    )
    gltf = to_glb.read_glb_json(tmp_path / "p.glb")
    assert gltf["meshes"][0]["primitives"][0]["mode"] == 0
    assert "contract" not in gltf["scenes"][0]["extras"]["clio"]  # not a viewport mesh


def test_ascii_pcd_is_read(tmp_path: Path) -> None:
    pcd = tmp_path / "c.pcd"
    pcd.write_text(
        "VERSION .7\nFIELDS x y z\nSIZE 4 4 4\nTYPE F F F\nCOUNT 1 1 1\nWIDTH 2\nHEIGHT 1\nPOINTS 2\nDATA ascii\n0 0 0\n1 2 3\n",
        encoding="utf-8",
    )
    xyz, colors = to_glb.load_points(pcd)
    assert xyz.tolist() == [[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]] and colors is None


def test_ply_mesh_via_trimesh(tmp_path: Path) -> None:
    import trimesh  # required, never skipped: the test command adds --with trimesh

    mesh = trimesh.Trimesh(
        vertices=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float),
        faces=[[0, 1, 2]],
        process=False,
    )
    ply = tmp_path / "tri.ply"
    mesh.export(ply)

    assert to_glb.main(["ply", str(ply), "-o", str(tmp_path / "tri.glb")]) == 0
    clio = to_glb.read_glb_json(tmp_path / "tri.glb")["scenes"][0]["extras"]["clio"]
    assert clio["counts"]["triangles"] == 1


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

    as_text = validate_views.validate_table(
        _design(treatment_value=["0", "50", "0"]), schema
    )
    assert any("treatment_value" in e for e in as_text["errors"])

    missing = validate_views.validate_table(pa.table({"genotype": ["g1"]}), schema)
    assert any("missing required columns" in e for e in missing["errors"])

    observations = validate_views.load_schema("observations")
    sentinel = validate_views.validate_table(
        _observations([10.0, FLOAT_MAX, 12.0]), observations
    )
    assert any("sentinel" in e for e in sentinel["errors"])

    bad_time = _observations().set_column(
        1, "time", pa.array(["yesterday", "2000-01-02", "2000-01-01"])
    )
    assert any(
        "ISO 8601" in e
        for e in validate_views.validate_table(bad_time, observations)["errors"]
    )


def test_every_seam_schema_is_valid_json_schema() -> None:
    import jsonschema

    for kind in validate_views.KINDS:
        schema = validate_views.load_schema(kind)
        jsonschema.Draft202012Validator.check_schema(schema)
        assert set(schema["x-primary-key"]) <= set(schema["properties"])
        assert set(schema["required"]) <= set(schema["properties"])
