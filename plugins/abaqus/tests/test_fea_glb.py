"""Exporter tests for abaqus-visualization/scripts (numpy only, no Abaqus).

``odb_to_glb.py`` is exercised end to end against a small fake of the
``odbAccess`` / ``abaqusConstants`` API surface it uses, so the frame loop,
density lookup, and nodal averaging run without an Abaqus license.
"""

from __future__ import annotations

import importlib.util
import struct
import sys
import types
from pathlib import Path

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "abaqus-visualization" / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fea_glb = _load("fea_glb")

# Two C3D8R bricks sharing the face x=1, written the way Abaqus writes a flat .inp.
TWO_BRICKS_INP = """*Heading
*Node
 1, 0., 0., 0.
 2, 1., 0., 0.
 3, 1., 1., 0.
 4, 0., 1., 0.
 5, 0., 0., 1.
 6, 1., 0., 1.
 7, 1., 1., 1.
 8, 0., 1., 1.
 9, 2., 0., 0.
10, 2., 1., 0.
11, 2., 0., 1.
12, 2., 1., 1.
*Element, type=C3D8R
1, 1, 2, 3, 4, 5, 6, 7, 8
2, 2, 9, 10, 3, 6, 11, 12,
7
*Nset, nset=All, generate
1, 12, 1
"""


def _bricks(tmp_path: Path):
    path = tmp_path / "bricks.inp"
    path.write_text(TWO_BRICKS_INP)
    return fea_glb.read_inp(str(path))


def _signed_volume(mesh) -> float:
    a, b, c = (mesh.positions[mesh.triangles[:, i]] for i in range(3))
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


def test_exterior_mesh_drops_the_shared_face_and_points_outward(tmp_path: Path) -> None:
    node_ids, coords, elements = _bricks(tmp_path)
    assert len(elements) == 2 and elements[1][1][-1] == 7, "continuation line is joined"
    mesh = fea_glb.exterior_mesh(node_ids, coords, elements)
    assert mesh.topology == "surface" and len(mesh.triangles) == 20
    assert _signed_volume(mesh) == pytest.approx(2.0)
    np.testing.assert_allclose(mesh.node_positions()[mesh.node_index], mesh.positions)


def test_keep_mask_removes_elements(tmp_path: Path) -> None:
    node_ids, coords, elements = _bricks(tmp_path)
    mesh = fea_glb.exterior_mesh(node_ids, coords, elements, keep=np.array([True, False]))
    assert len(mesh.triangles) == 12
    assert _signed_volume(mesh) == pytest.approx(1.0)


def test_cell_mesh_records_both_sides_of_every_face(tmp_path: Path) -> None:
    node_ids, coords, elements = _bricks(tmp_path)
    mesh = fea_glb.cell_mesh(node_ids, coords, elements)
    assert mesh.topology == "cells" and mesh.cells == 2
    assert len(mesh.triangles) == 22, "11 unique quads: 10 outer + the shared one"
    per_face = {(int(a), int(b)) for a, b in zip(mesh.cell_a[::4], mesh.cell_b[::4])}
    assert per_face == {(0, -1), (1, -1), (0, 1)}
    boundary = mesh.triangles[mesh.cell_b[mesh.triangles[:, 0]] == -1]
    outer = fea_glb.Mesh(mesh.positions, boundary, mesh.node_index)
    assert _signed_volume(outer) == pytest.approx(2.0), "faces point out of cell a"


def test_hierarchical_inp_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "part.inp"
    path.write_text("*Part, name=Block\n*Node\n1, 0., 0., 0.\n")
    with pytest.raises(ValueError, match="Instance"):
        fea_glb.read_inp(str(path))


def test_glb_roundtrip_with_frames_and_cell_fields(tmp_path: Path) -> None:
    node_ids, coords, elements = _bricks(tmp_path)
    mesh = fea_glb.cell_mesh(node_ids, coords, elements)
    density = np.array([[1.0, 1.0], [1.0, 0.4], [1.0, 0.1]])
    mises = np.linspace(0, 11, 12)
    out = tmp_path / "cells.glb"
    meta = fea_glb.write_glb(
        str(out), mesh,
        [fea_glb.Field("DENSITY", density), fea_glb.Field("S_MISES", mises)],
        stage="optimized", source={"kind": "t"}, frames=["Cycle 0", "Cycle 1", "Cycle 2"],
    )
    assert meta["topology"] == "cells"
    assert [f["label"] for f in meta["frames"]] == ["Cycle 0", "Cycle 1", "Cycle 2"]
    dens = next(f for f in meta["fields"] if f["name"] == "DENSITY")
    assert (dens["location"], dens["frames"], dens["count"], dens["min"]) == ("cell", 3, 2, pytest.approx(0.1))

    data = out.read_bytes()
    assert struct.unpack("<4sII", data[:12]) == (b"glTF", 2, len(data))
    back, fields, back_meta = fea_glb.read_glb(str(out))
    np.testing.assert_array_equal(back.cell_b, mesh.cell_b)
    np.testing.assert_array_equal(back.node_index, mesh.node_index)
    by_name = {f.name: f for f in fields}
    np.testing.assert_allclose(by_name["DENSITY"].values, density)
    np.testing.assert_allclose(by_name["S_MISES"].values[0], mises)
    assert back_meta["counts"] == {"vertices": 44, "triangles": 22, "nodes": 12, "cells": 2}
    assert back_meta["bounds"] == {"min": [0, 0, 0], "max": [2, 1, 1]}
    assert "enclosed_volume" not in back_meta, "a cells export is not a closed surface"


def test_surface_export_reports_its_enclosed_volume(tmp_path: Path) -> None:
    node_ids, coords, elements = _bricks(tmp_path)
    out = tmp_path / "s.glb"
    meta = fea_glb.write_glb(str(out), fea_glb.exterior_mesh(node_ids, coords, elements),
                             stage="baseline", source={})
    assert meta["enclosed_volume"] == pytest.approx(2.0)


def test_field_shape_is_checked_against_the_mesh(tmp_path: Path) -> None:
    node_ids, coords, elements = _bricks(tmp_path)
    surface = fea_glb.exterior_mesh(node_ids, coords, elements)
    with pytest.raises(ValueError, match="values per frame"):
        fea_glb.write_glb(str(tmp_path / "x.glb"), surface, [fea_glb.Field("S_MISES", np.zeros(3))],
                          stage="baseline", source={})
    with pytest.raises(ValueError, match="cells-topology"):
        fea_glb.write_glb(str(tmp_path / "x.glb"), surface, [fea_glb.Field("DENSITY", np.ones(2))],
                          stage="baseline", source={})


def test_ascii_and_binary_stl_weld_to_the_same_mesh(tmp_path: Path) -> None:
    tri = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]], [[1, 0, 0], [1, 1, 0], [0, 1, 0]]], float)
    ascii_path = tmp_path / "a.stl"
    lines = ["solid s"]
    for face in tri:
        lines += ["facet normal 0 0 1", " outer loop"]
        lines += [f"  vertex {x} {y} {z}" for x, y, z in face]
        lines += [" endloop", "endfacet"]
    ascii_path.write_text("\n".join(lines + ["endsolid s"]))
    binary_path = tmp_path / "b.stl"
    body = b"".join(struct.pack("<3f", 0, 0, 1) + face.astype("<f4").tobytes() + b"\0\0" for face in tri)
    binary_path.write_bytes(b"\0" * 80 + struct.pack("<I", len(tri)) + body)
    for path in (ascii_path, binary_path):
        positions, triangles = fea_glb.read_stl(str(path))
        assert len(positions) == 4 and len(triangles) == 2


def test_projection_carries_every_frame() -> None:
    source = np.array([[0, 0, 0], [10, 0, 0]], dtype=float)
    values = np.array([[5.0, 50.0], [6.0, 60.0]])
    target = np.array([[1, 0, 0], [9, 1, 0]], dtype=float)
    np.testing.assert_allclose(fea_glb.project_nearest(source, values, target), [[5, 50], [6, 60]])


def test_stl_projection_uses_only_exported_surface_nodes(tmp_path: Path) -> None:
    node_ids, coords, elements = _bricks(tmp_path)
    source_mesh = fea_glb.exterior_mesh(node_ids, coords, elements)
    fe = tmp_path / "fe.glb"
    fea_glb.write_glb(str(fe), source_mesh, [fea_glb.Field("S_MISES", np.arange(12.0))],
                      stage="optimized", source={})
    stl = tmp_path / "s.stl"
    stl.write_text("solid s\nfacet normal 0 0 1\n outer loop\n  vertex 0 0 0\n  vertex 2 0 0\n"
                   "  vertex 2 1 1\n endloop\nendfacet\nendsolid s\n")
    out = tmp_path / "o.glb"
    assert fea_glb._main(["stl", str(stl), "-o", str(out), "--stage", "optimized",
                          "--project-from", str(fe)]) == 0
    _, fields, _ = fea_glb.read_glb(str(out))
    np.testing.assert_allclose(sorted(fields[0].values[0]), [0.0, 8.0, 11.0])


# ------------------------------------------------------------- odb_to_glb


class _Value:
    def __init__(self, data, node=None, element=None):
        self.data, self.nodeLabel, self.elementLabel = data, node, element


class _Block:
    def __init__(self, node_labels, data):
        self.nodeLabels, self.data = node_labels, data


class _FieldOutput:
    def __init__(self, values=(), blocks=()):
        self.values, self.bulkDataBlocks = list(values), list(blocks)

    def getSubset(self, **_):
        return self

    def getScalarField(self, **_):
        return self


class _Frame:
    def __init__(self, frame_id, outputs):
        self.frameId, self.fieldOutputs = frame_id, outputs


def _fake_abaqus(monkeypatch, frames, instance):
    odb = types.SimpleNamespace(
        rootAssembly=types.SimpleNamespace(instances={"PART-1": instance}),
        steps={"Step-1": types.SimpleNamespace(frames=frames)},
        close=lambda: None,
    )
    odb.steps = _Steps(odb.steps)
    monkeypatch.setitem(sys.modules, "odbAccess", types.SimpleNamespace(openOdb=lambda *a, **k: odb))
    monkeypatch.setitem(sys.modules, "abaqusConstants",
                        types.SimpleNamespace(ELEMENT_NODAL="EN", MISES="MISES"))


class _Steps(dict):
    def keys(self):  # Abaqus returns an indexable key list
        return list(super().keys())


class _Outputs(dict):
    def keys(self):
        return list(super().keys())


def test_odb_export_reads_density_for_every_cycle(tmp_path: Path, monkeypatch) -> None:
    odb_to_glb = _load("odb_to_glb")
    node_ids, coords, elements = _bricks(tmp_path)
    instance = types.SimpleNamespace(
        name="PART-1",
        nodes=[types.SimpleNamespace(label=int(n), coordinates=tuple(c)) for n, c in zip(node_ids, coords)],
        elements=[types.SimpleNamespace(label=i + 1, type="C3D8R", connectivity=conn)
                  for i, (_, conn) in enumerate(elements)],
    )
    labels = list(range(1, 13))
    frames = []
    for cycle, second in enumerate((1.0, 0.5, 0.2)):
        frames.append(_Frame(cycle, _Outputs({
            "S": _FieldOutput(blocks=[_Block(labels, np.full(12, 10.0 * (cycle + 1)))]),
            "MAT_PROP_NORMALIZED": _FieldOutput(values=[_Value(1.0, element=1), _Value(second, element=2)]),
        })))
    _fake_abaqus(monkeypatch, frames, instance)
    out = tmp_path / "design.glb"
    assert odb_to_glb.main(["x.odb", "-o", str(out), "--stage", "optimized", "--cells",
                            "--frames", "all", "--frame-label", "Cycle"]) == 0
    mesh, fields, meta = fea_glb.read_glb(str(out))
    assert mesh.topology == "cells"
    assert [f["label"] for f in meta["frames"]] == ["Cycle 0", "Cycle 1", "Cycle 2"]
    by_name = {f.name: f for f in fields}
    np.testing.assert_allclose(by_name["DENSITY"].values, [[1, 1], [1, 0.5], [1, 0.2]])
    np.testing.assert_allclose(by_name["S_MISES"].values[:, 0], [10, 20, 30])


def test_odb_iso_export_keeps_dense_elements(tmp_path: Path, monkeypatch) -> None:
    odb_to_glb = _load("odb_to_glb")
    node_ids, coords, elements = _bricks(tmp_path)
    instance = types.SimpleNamespace(
        name="PART-1",
        nodes=[types.SimpleNamespace(label=int(n), coordinates=tuple(c)) for n, c in zip(node_ids, coords)],
        elements=[types.SimpleNamespace(label=i + 1, type="C3D8R", connectivity=conn)
                  for i, (_, conn) in enumerate(elements)],
    )
    frame = _Frame(4, _Outputs({
        "MAT_PROP_NORMALIZED": _FieldOutput(values=[_Value(0.9, element=1), _Value(0.1, element=2)]),
    }))
    _fake_abaqus(monkeypatch, [frame], instance)
    out = tmp_path / "fe.glb"
    assert odb_to_glb.main(["x.odb", "-o", str(out), "--stage", "optimized", "--iso", "0.3"]) == 0
    mesh, fields, meta = fea_glb.read_glb(str(out))
    assert mesh.topology == "surface" and len(mesh.triangles) == 12
    assert meta["source"]["kept_elements"] == 1
    assert fields == [], "density stays out of surface exports"


def test_render_view_draws_the_thresholded_frame(tmp_path: Path) -> None:
    render_view = _load("render_view")
    node_ids, coords, elements = _bricks(tmp_path)
    mesh = fea_glb.cell_mesh(node_ids, coords, elements)
    glb = tmp_path / "cells.glb"
    fea_glb.write_glb(str(glb), mesh, [fea_glb.Field("DENSITY", [[1.0, 1.0], [1.0, 0.1]])],
                      stage="optimized", source={}, frames=["Cycle 0", "Cycle 1"])
    loaded, fields, _ = fea_glb.read_glb(str(glb))
    threshold = (fields[0], 0.3, 1.0)
    shown, cells = render_view.visible_triangles(loaded, fields, 1, threshold)
    assert len(shown) == 12 and set(cells.tolist()) == {0}
    out = tmp_path / "fig.png"
    result = render_view.render(str(glb), str(out), "DENSITY", 1, ("DENSITY", 0.3, 1.0),
                                camera={"position": [30, 20, 30], "target": [10, 5, 5]})
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert result["triangles"] == 12 and result["frame"].startswith("Cycle 1")
