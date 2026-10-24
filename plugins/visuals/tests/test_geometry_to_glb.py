"""Tests for the geometry-to-glb converter (the clio.mesh-viewport.v1 GLB writer)."""

from __future__ import annotations

import hashlib
import importlib.util
import struct
import sys
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

PLUGIN = Path(__file__).resolve().parents[1]


def load_script(relative: str, name: str) -> ModuleType:
    """Import a skill script by path (scripts are not a package)."""

    path = PLUGIN / relative
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


to_glb = load_script("skills/geometry-to-glb/scripts/to_glb.py", "visuals_to_glb")

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
    assert segment["name"] == "SEGMENT" and segment["location"] == "node" and segment["count"] == 4
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
    assert {k: v for k, v in tree_hash(tmp_path).items() if not k.startswith("out/")} == before


def test_one_based_quads_are_detected_and_split(tmp_path: Path) -> None:
    v, f, _ = _geometry(tmp_path, faces="1 2 3 4\n")
    out = tmp_path / "quad.glb"

    assert to_glb.main(["mesh", "--vertices", str(v), "--faces", str(f), "-o", str(out)]) == 0

    clio = to_glb.read_glb_json(out)["scenes"][0]["extras"]["clio"]
    assert clio["conversion"] == {"index_base_detected": 1, "quads_split": True}
    assert clio["counts"]["triangles"] == 2
    assert clio["fields"] == []


def test_bad_geometry_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
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
        to_glb.main(["points", str(points), "-o", str(tmp_path / "p.glb"), "--allow-points"]) == 0
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
