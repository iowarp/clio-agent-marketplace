"""Turn Abaqus/Tosca geometry and results into viewport-ready .glb files.

The output is a standard glTF 2.0 binary with one triangle mesh, read by the
``clio.mesh-viewport.v1`` A2UI kernel. The contract (``clio.fea-mesh.v1``):

* Vertex attribute ``_NODE`` maps each vertex to a row of the node arrays.
* ``topology: "surface"`` meshes are an outer surface only (STL, the outer
  faces of an FE mesh). ``topology: "cells"`` meshes carry every element face
  plus ``_CELL_A`` / ``_CELL_B``: the elements on either side of the face
  (``-1`` on the model boundary). That lets the viewer threshold elements by
  a cell field and rebuild the visible surface, like ParaView's Threshold.
* Every field is a standalone accessor, listed in ``scenes[0].extras.clio``
  with its location (``node`` or ``cell``), label, unit, and range. A field
  may have several frames (design cycles, increments), stored frame-major.
  ``extras.clio.frames`` names them.

Only the standard library and numpy are used, so this file runs inside Abaqus
Python (``odb_to_glb.py`` imports it) and in any ordinary Python 3.

Commands::

    python fea_glb.py inp Block_flat.inp -o baseline.glb --stage baseline
    python fea_glb.py inp Block_flat.inp -o cells.glb --stage baseline --cells
    python fea_glb.py stl ISO_SMOOTHING.stl -o optimized.glb --stage optimized \\
        --project-from optimized_fe.glb
    python fea_glb.py info optimized.glb
"""

from __future__ import annotations

import argparse
import json
import struct
import sys

import numpy as np

CONTRACT = "clio.fea-mesh.v1"

# Corner order of each solid face, 1-based as in the Abaqus element library
# (S1..S6 for hexahedra, S1..S4 for tetrahedra, S1..S5 for wedges). Listed in
# the library's order, whose right-hand normal points into the element, so
# faces are reversed to point outward. Only corner nodes are used; midside
# nodes of quadratic elements never reach the viewport.
_FACES = {
    "hex": ((1, 2, 3, 4), (5, 8, 7, 6), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 8, 4), (4, 8, 5, 1)),
    "tet": ((1, 2, 3), (1, 4, 2), (2, 4, 3), (3, 4, 1)),
    "wedge": ((1, 2, 3), (4, 6, 5), (1, 4, 5, 2), (2, 5, 6, 3), (3, 6, 4, 1)),
}
_CORNERS = {"hex": 8, "tet": 4, "wedge": 6}

#: Known fields: label, unit, and where Abaqus/Tosca define them.
FIELD_INFO = {
    "S_MISES": ("von Mises stress", "MPa", "node"),
    "U_MAG": ("Displacement magnitude", "mm", "node"),
    "PEEQ": ("Equivalent plastic strain", "", "node"),
    "DENSITY": ("Relative density", "", "cell"),  # Tosca's 0 to 1 scale
}


class Field:
    """One result: ``values`` has shape ``(frames, count)`` or ``(count,)``."""

    def __init__(self, name, values, location=None, label=None, unit=None):
        info = FIELD_INFO.get(name.upper(), (name, "", "node"))
        self.name = name.upper()
        self.location = location or info[2]
        self.label = label or info[0]
        self.unit = info[1] if unit is None else unit
        values = np.asarray(values, dtype=np.float64)
        self.values = values.reshape(1, -1) if values.ndim == 1 else values

    @property
    def frames(self):
        return self.values.shape[0]

    @property
    def count(self):
        return self.values.shape[1]


class Mesh:
    """Positions and triangles plus the index maps the viewer needs."""

    def __init__(self, positions, triangles, node_index, cell_a=None, cell_b=None,
                 nodes=0, cells=0):
        self.positions = np.asarray(positions, dtype=np.float64)
        self.triangles = np.asarray(triangles, dtype=np.int64)
        self.node_index = np.asarray(node_index, dtype=np.int64)
        self.cell_a = None if cell_a is None else np.asarray(cell_a, dtype=np.int64)
        self.cell_b = None if cell_b is None else np.asarray(cell_b, dtype=np.int64)
        self.nodes = int(nodes)
        self.cells = int(cells)

    @property
    def topology(self):
        return "cells" if self.cell_a is not None else "surface"

    def node_positions(self):
        """Coordinates of each node row (for projection and tests)."""

        out = np.zeros((self.nodes, 3))
        out[self.node_index] = self.positions
        return out


def element_family(abaqus_type):
    """Map an Abaqus element type name to a face-table family, or None."""

    name = abaqus_type.upper()
    if name.startswith("C3D8") or name.startswith("C3D20") or name.startswith("SC8"):
        return "hex"
    if name.startswith("C3D4") or name.startswith("C3D10"):
        return "tet"
    if name.startswith("C3D6") or name.startswith("C3D15") or name.startswith("SC6"):
        return "wedge"
    return None


# ---------------------------------------------------------------- readers


def read_inp(path):
    """Read nodes and solid elements from a flattened (Tosca-style) .inp.

    Returns ``(node_ids, coords, elements)``; ``elements`` is a list of
    ``(family, connectivity)`` with connectivity as node ids. Inputs with
    *Part/*Instance blocks go through ``odb_to_glb.py`` instead.
    """

    node_ids, coords, elements = [], [], []
    mode, family, pending = None, None, []
    with open(path) as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("**"):
                continue
            if line.startswith("*"):
                pending = []
                keyword = line.split(",")[0].strip().upper()
                if keyword == "*NODE":
                    mode = "node"
                elif keyword == "*ELEMENT":
                    params = dict(
                        part.strip().split("=", 1) for part in line.split(",")[1:] if "=" in part
                    )
                    params = {k.strip().upper(): v.strip() for k, v in params.items()}
                    family = element_family(params.get("TYPE", ""))
                    mode = "element" if family else None
                elif keyword in ("*PART", "*INSTANCE"):
                    raise ValueError(
                        "%s has *Part/*Instance blocks; flatten it or export from the ODB" % path
                    )
                else:
                    mode = None
                continue
            if mode == "node":
                values = [v for v in line.split(",") if v.strip()]
                node_ids.append(int(values[0]))
                coords.append([float(v) for v in values[1:4]])
            elif mode == "element":
                values = [int(v) for v in line.split(",") if v.strip()]
                pending.extend(values)
                if line.endswith(","):
                    continue  # connectivity continues on the next line
                elements.append((family, tuple(pending[1 : 1 + _CORNERS[family]])))
                pending = []
    if not coords:
        raise ValueError("no *Node block found in %s" % path)
    return np.asarray(node_ids, dtype=np.int64), np.asarray(coords, dtype=np.float64), elements


def read_stl(path):
    """Read an ASCII or binary STL; returns welded ``(positions, triangles)``."""

    with open(path, "rb") as handle:
        data = handle.read()
    count = struct.unpack("<I", data[80:84])[0] if len(data) >= 84 else -1
    if count >= 0 and len(data) == 84 + 50 * count:
        records = np.frombuffer(data, dtype=np.uint8, offset=84).reshape(count, 50)
        corners = records[:, 12:48].copy().view("<f4").reshape(count * 3, 3)
    else:
        text = data.decode("ascii", errors="replace").split()
        values = [
            (float(text[i + 1]), float(text[i + 2]), float(text[i + 3]))
            for i, token in enumerate(text)
            if token == "vertex"
        ]
        corners = np.asarray(values, dtype=np.float64)
    if len(corners) == 0 or len(corners) % 3:
        raise ValueError("%s is not a triangle STL" % path)
    rounded = np.round(corners.astype(np.float64), 6)
    positions, inverse = np.unique(rounded, axis=0, return_inverse=True)
    triangles = inverse.reshape(-1, 3).astype(np.int64)
    degenerate = (
        (triangles[:, 0] == triangles[:, 1])
        | (triangles[:, 1] == triangles[:, 2])
        | (triangles[:, 0] == triangles[:, 2])
    )
    return positions, triangles[~degenerate]


# ---------------------------------------------------------------- meshes


def _faces(node_ids, elements):
    """Unique element faces: ``{sorted key: [outward corner rows, cell a, cell b]}``."""

    index_of = {int(n): i for i, n in enumerate(node_ids)}
    faces = {}
    for cell, (family, conn) in enumerate(elements):
        for face in _FACES[family]:
            corners = tuple(index_of[conn[i - 1]] for i in face)
            key = tuple(sorted(corners))
            entry = faces.get(key)
            if entry is None:
                faces[key] = [tuple(reversed(corners)), cell, -1]  # outward from cell a
            else:
                entry[2] = cell
    return faces


def surface_mesh(positions, triangles):
    """A surface-topology mesh whose vertices are its nodes (STL, projections)."""

    positions = np.asarray(positions, dtype=np.float64)
    return Mesh(positions, triangles, np.arange(len(positions)), nodes=len(positions))


def exterior_mesh(node_ids, coords, elements, keep=None):
    """Outer surface of a solid mesh; node rows follow ``node_ids``.

    ``keep`` is an optional boolean mask over ``elements`` (for example the
    elements whose Tosca density is at or above the iso level).
    """

    kept = [e if keep is None or keep[i] else None for i, e in enumerate(elements)]
    live = [(i, e) for i, e in enumerate(kept) if e is not None]
    faces = _faces(node_ids, [e for _, e in live])
    rings = [ring for ring, _, b in faces.values() if b == -1]
    if not rings:
        raise ValueError("mesh has no exterior faces (all elements removed?)")
    triangles = []
    for ring in rings:
        triangles.append((ring[0], ring[1], ring[2]))
        if len(ring) == 4:
            triangles.append((ring[0], ring[2], ring[3]))
    triangles = np.asarray(triangles, dtype=np.int64)
    used, compact = np.unique(triangles, return_inverse=True)
    return Mesh(
        np.asarray(coords, dtype=np.float64)[used], compact.reshape(-1, 3), used,
        nodes=len(node_ids),
    )


def cell_mesh(node_ids, coords, elements):
    """Every unique element face, with the cells on each side, for thresholding.

    Face corners are not shared between faces, so each face shades flat and
    carries its own ``_CELL_A`` / ``_CELL_B`` values.
    """

    coords = np.asarray(coords, dtype=np.float64)
    positions, triangles, node_index, cell_a, cell_b = [], [], [], [], []
    for ring, a, b in _faces(node_ids, elements).values():
        base = len(node_index)
        node_index.extend(ring)
        cell_a.extend([a] * len(ring))
        cell_b.extend([b] * len(ring))
        triangles.append((base, base + 1, base + 2))
        if len(ring) == 4:
            triangles.append((base, base + 2, base + 3))
    node_index = np.asarray(node_index, dtype=np.int64)
    return Mesh(coords[node_index], triangles, node_index, cell_a, cell_b,
                nodes=len(node_ids), cells=len(elements))


def project_nearest(source_positions, source_values, target_positions, chunk=4096):
    """Carry node values onto new points by nearest source point (numpy only).

    ``source_values`` may be ``(count,)`` or ``(frames, count)``.
    """

    source = np.asarray(source_positions, dtype=np.float64)
    target = np.asarray(target_positions, dtype=np.float64)
    nearest = np.empty(len(target), dtype=np.int64)
    source_sq = (source**2).sum(axis=1)
    for start in range(0, len(target), chunk):
        block = target[start : start + chunk]
        nearest[start : start + chunk] = np.argmin(source_sq[None, :] - 2.0 * block @ source.T, axis=1)
    values = np.asarray(source_values, dtype=np.float64)
    return values[..., nearest]


# ---------------------------------------------------------------- writer


def _pad(blob, fill=b"\x00"):
    return blob + fill * ((4 - len(blob) % 4) % 4)


def write_glb(path, mesh, fields=(), *, stage, source, frames=None, units="mm", extra=None):
    """Write ``mesh`` and ``fields`` as one .glb following ``clio.fea-mesh.v1``.

    ``frames`` optionally labels the frames of frame-varying fields, e.g.
    ``["Cycle 0", "Cycle 1", ...]``; every multi-frame field must match it.
    """

    fields = list(fields)
    frame_count = max([f.frames for f in fields] + [1])
    labels = list(frames) if frames is not None else [str(i) for i in range(frame_count)]
    for field in fields:
        if field.location == "cell" and mesh.topology != "cells":
            raise ValueError("cell field %s needs a cells-topology mesh" % field.name)
        expected = mesh.cells if field.location == "cell" else mesh.nodes
        if field.count != expected:
            raise ValueError(
                "field %s has %d values per frame for %d %ss"
                % (field.name, field.count, expected, field.location)
            )
        if field.frames not in (1, len(labels)):
            raise ValueError("field %s has %d frames, expected %d" % (field.name, field.frames, len(labels)))

    buffers, views, accessors = [], [], []
    offset = 0

    def add(array, kind, target=None, minmax=False, component=5126):
        nonlocal offset
        array = np.ascontiguousarray(array, dtype="<f4" if component == 5126 else "<u4")
        view = {"buffer": 0, "byteOffset": offset, "byteLength": array.nbytes}
        if target:
            view["target"] = target
        views.append(view)
        accessor = {"bufferView": len(views) - 1, "componentType": component,
                    "count": int(array.shape[0]), "type": kind}
        if minmax:
            flat = array.reshape(array.shape[0], -1)
            accessor["min"] = [float(v) for v in flat.min(axis=0)]
            accessor["max"] = [float(v) for v in flat.max(axis=0)]
        accessors.append(accessor)
        blob = _pad(array.tobytes())
        buffers.append(blob)
        offset += len(blob)
        return len(accessors) - 1

    attributes = {
        "POSITION": add(mesh.positions, "VEC3", 34962, minmax=True),
        "_NODE": add(mesh.node_index, "SCALAR", 34962),
    }
    if mesh.topology == "cells":
        attributes["_CELL_A"] = add(mesh.cell_a, "SCALAR", 34962)
        attributes["_CELL_B"] = add(mesh.cell_b, "SCALAR", 34962)
    indices = add(mesh.triangles.reshape(-1), "SCALAR", 34963, component=5125)

    field_meta = []
    for field in fields:
        data = field.values
        field_meta.append({
            "name": field.name, "label": field.label, "unit": field.unit,
            "location": field.location, "count": field.count, "frames": field.frames,
            "accessor": add(data.reshape(-1), "SCALAR"),
            "min": float(np.nanmin(data)), "max": float(np.nanmax(data)),
        })

    clio = {
        "contract": CONTRACT,
        "stage": stage,
        "topology": mesh.topology,
        "units": {"length": units},
        "source": source,
        "fields": field_meta,
        "frames": [{"label": label} for label in labels] if frame_count > 1 else [],
        "counts": {"vertices": int(len(mesh.positions)), "triangles": int(len(mesh.triangles)),
                   "nodes": mesh.nodes, "cells": mesh.cells},
        "bounds": {"min": [float(v) for v in mesh.positions.min(axis=0)],
                   "max": [float(v) for v in mesh.positions.max(axis=0)]},
    }
    if mesh.topology == "surface":
        # Signed volume of the closed surface: the sanity check for an iso
        # surface (compare it with the design domain before showing it).
        a, b, c = (mesh.positions[mesh.triangles[:, i]] for i in range(3))
        clio["enclosed_volume"] = float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)
    if extra:
        clio.update(extra)
    gltf = {
        "asset": {"version": "2.0", "generator": "clio fea_glb"},
        "scene": 0,
        "scenes": [{"nodes": [0], "extras": {"clio": clio}}],
        "nodes": [{"mesh": 0, "name": stage}],
        "meshes": [{"name": stage, "primitives": [{"attributes": attributes, "indices": indices, "mode": 4}]}],
        "buffers": [{"byteLength": offset}],
        "bufferViews": views,
        "accessors": accessors,
    }
    json_chunk = _pad(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), b" ")
    bin_chunk = b"".join(buffers)
    total = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    with open(path, "wb") as handle:
        handle.write(struct.pack("<4sII", b"glTF", 2, total))
        handle.write(struct.pack("<I4s", len(json_chunk), b"JSON") + json_chunk)
        handle.write(struct.pack("<I4s", len(bin_chunk), b"BIN\x00") + bin_chunk)
    return clio


def read_glb(path):
    """Read back a .glb written by :func:`write_glb`: ``(mesh, fields, meta)``."""

    with open(path, "rb") as handle:
        data = handle.read()
    magic, version, _ = struct.unpack("<4sII", data[:12])
    if magic != b"glTF" or version != 2:
        raise ValueError("%s is not a glTF 2.0 binary" % path)
    json_len = struct.unpack("<I", data[12:16])[0]
    gltf = json.loads(data[20 : 20 + json_len])
    blob = data[20 + json_len + 8 :]

    def accessor(index):
        acc = gltf["accessors"][index]
        view = gltf["bufferViews"][acc["bufferView"]]
        dtype = {5126: "<f4", 5125: "<u4"}[acc["componentType"]]
        width = {"SCALAR": 1, "VEC3": 3}[acc["type"]]
        arr = np.frombuffer(blob, dtype=dtype, count=acc["count"] * width, offset=view["byteOffset"])
        return arr.reshape(acc["count"], width) if width > 1 else arr

    meta = gltf["scenes"][0]["extras"]["clio"]
    attributes = gltf["meshes"][0]["primitives"][0]["attributes"]
    counts = meta["counts"]
    mesh = Mesh(
        accessor(attributes["POSITION"]),
        accessor(gltf["meshes"][0]["primitives"][0]["indices"]).reshape(-1, 3),
        accessor(attributes["_NODE"]).astype(np.int64),
        accessor(attributes["_CELL_A"]).astype(np.int64) if "_CELL_A" in attributes else None,
        accessor(attributes["_CELL_B"]).astype(np.int64) if "_CELL_B" in attributes else None,
        nodes=counts["nodes"], cells=counts["cells"],
    )
    fields = [
        Field(f["name"], accessor(f["accessor"]).reshape(f["frames"], f["count"]),
              f["location"], f["label"], f["unit"])
        for f in meta["fields"]
    ]
    return mesh, fields, meta


# ---------------------------------------------------------------- CLI


def _main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    inp = sub.add_parser("inp", help="FE mesh from a flattened .inp (geometry only)")
    inp.add_argument("path")
    inp.add_argument("--cells", action="store_true", help="keep every element face for thresholding")
    stl = sub.add_parser("stl", help="Tosca ISO/VOLUME smoothing STL")
    stl.add_argument("path")
    stl.add_argument("--project-from", help=".glb whose node fields are carried onto the STL")
    for command in (inp, stl):
        command.add_argument("-o", "--output", required=True)
        command.add_argument("--stage", required=True, choices=("baseline", "optimized"))
        command.add_argument("--units", default="mm")
    info = sub.add_parser("info", help="print the clio metadata of a .glb")
    info.add_argument("path")
    args = parser.parse_args(argv)

    if args.command == "info":
        print(json.dumps(read_glb(args.path)[2], indent=2))
        return 0
    if args.command == "inp":
        node_ids, coords, elements = read_inp(args.path)
        mesh = cell_mesh(node_ids, coords, elements) if args.cells else exterior_mesh(node_ids, coords, elements)
        meta = write_glb(args.output, mesh, stage=args.stage, units=args.units,
                         source={"kind": "inp", "path": args.path, "elements": len(elements)})
    else:
        positions, triangles = read_stl(args.path)
        mesh = surface_mesh(positions, triangles)
        fields, frames, source = [], None, {"kind": "stl", "path": args.path}
        if args.project_from:
            src_mesh, src_fields, src_meta = read_glb(args.project_from)
            src_nodes = src_mesh.node_positions()
            used = np.zeros(src_mesh.nodes, dtype=bool)
            used[src_mesh.node_index] = True  # only nodes on the exported surface
            for field in src_fields:
                if field.location == "node":
                    values = project_nearest(src_nodes[used], field.values[:, used], positions)
                    fields.append(Field(field.name, values, "node", field.label, field.unit))
            frames = [f["label"] for f in src_meta.get("frames", [])] or None
            source["fields_from"] = {"path": args.project_from, "method": "nearest-node",
                                     "source": src_meta.get("source")}
        meta = write_glb(args.output, mesh, fields, stage=args.stage, units=args.units,
                         source=source, frames=frames)
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
