# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy>=1.24"]
# ///
"""Convert plain-text or PLY/PCD geometry into a .glb for clio's mesh viewport.

The output follows the ``clio.fea-mesh.v1`` contract that ``clio.mesh-viewport.v1``
reads: one indexed triangle mesh (``POSITION`` + ``_NODE``), standalone
per-vertex field accessors described in ``scenes[0].extras.clio``, and units.
Per-vertex colours are written two ways: as standard ``COLOR_0`` (for other
glTF viewers) and as a ``SEGMENT`` node field -- one integer per distinct
colour -- because the viewport colours by fields, not by vertex colours.

Inputs:

* ``mesh``: headerless, whitespace-delimited text triplets: vertices (V x 3
  floats), faces (F x 3 or F x 4 vertex indices; quads are split), and
  optional colours (V x 3; 0-255 integers or 0-1 floats).
* ``ply``: a .ply file with faces (needs ``trimesh``: add ``--with trimesh``).
* ``points`` / ``pcd``: a point cloud (text x y z [r g b], or ASCII .pcd).
  The mesh viewport renders triangles only, so points are REFUSED unless
  ``--allow-points`` is given; that writes a plain glTF POINTS file that other
  viewers can open but ``clio.mesh-viewport.v1`` cannot.
* ``info``: print the metadata of an existing .glb.

Usage::

    python to_glb.py mesh --vertices V.txt --faces F.txt [--colors C.txt] -o out.glb [--units mm]
    python to_glb.py ply surface.ply -o out.glb
    python to_glb.py points cloud.txt -o cloud.glb --allow-points
    python to_glb.py info out.glb

Inputs are only read; only ``-o`` is written.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path
from typing import Any

import numpy as np

CONTRACT = "clio.fea-mesh.v1"
FLOAT, UINT32 = 5126, 5125
ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER = 34962, 34963
#: More distinct colours than this is shading/texture, not a segmentation.
MAX_SEGMENTS = 256


class GeometryError(ValueError):
    """Input geometry that cannot be converted faithfully."""


def load_text(path: Path, columns: int | None = None) -> np.ndarray:
    """Load a headerless whitespace-delimited numeric text file as a 2-D array."""

    try:
        data = np.loadtxt(path, dtype=np.float64, ndmin=2)
    except ValueError as exc:
        raise GeometryError(
            f"{path.name}: not a headerless numeric text table ({exc})"
        ) from exc
    if data.size == 0:
        raise GeometryError(f"{path.name}: empty")
    if columns is not None and data.shape[1] < columns:
        raise GeometryError(
            f"{path.name}: expected at least {columns} columns, found {data.shape[1]}"
        )
    return data


def triangulate(
    faces: np.ndarray, vertex_count: int, index_base: str = "auto"
) -> tuple[np.ndarray, dict[str, Any]]:
    """Return (F' x 3 uint32 zero-based triangles, notes); splits quads, drops degenerates."""

    notes: dict[str, Any] = {}
    if not np.all(np.equal(np.mod(faces, 1), 0)):
        raise GeometryError("face indices are not integers")
    faces = faces.astype(np.int64)
    if faces.shape[1] not in (3, 4):
        raise GeometryError(
            f"faces must have 3 or 4 indices per row, found {faces.shape[1]}"
        )
    base = index_base
    if base == "auto":
        base = "1" if faces.min() >= 1 and faces.max() == vertex_count else "0"
        notes["index_base_detected"] = int(base)
    if base == "1":
        faces = faces - 1
    if faces.min() < 0 or faces.max() >= vertex_count:
        raise GeometryError(
            f"face indices out of range [0, {vertex_count - 1}] (min {faces.min()}, max {faces.max()}); "
            "check --index-base"
        )
    if faces.shape[1] == 4:
        faces = np.vstack([faces[:, [0, 1, 2]], faces[:, [0, 2, 3]]])
        notes["quads_split"] = True
    degenerate = (
        (faces[:, 0] == faces[:, 1])
        | (faces[:, 1] == faces[:, 2])
        | (faces[:, 0] == faces[:, 2])
    )
    if degenerate.any():
        notes["degenerate_triangles_dropped"] = int(degenerate.sum())
        faces = faces[~degenerate]
    if faces.size == 0:
        raise GeometryError("no non-degenerate triangles")
    return faces.astype(np.uint32), notes


def normalise_colors(colors: np.ndarray, vertex_count: int) -> np.ndarray:
    """Return V x 3 float colours in [0, 1] from 0-255 ints or 0-1 floats."""

    if colors.shape[0] != vertex_count:
        raise GeometryError(
            f"colours have {colors.shape[0]} rows for {vertex_count} vertices"
        )
    rgb = colors[:, :3].astype(np.float64)
    if rgb.min() < 0:
        raise GeometryError("negative colour values")
    if rgb.max() > 1.0:
        if rgb.max() > 255:
            raise GeometryError("colour values above 255")
        rgb = rgb / 255.0
    return rgb


def segment_ids(rgb: np.ndarray) -> tuple[np.ndarray, list[list[int]]]:
    """One integer per distinct colour (sorted by colour, so deterministic)."""

    quantised = np.round(rgb * 255).astype(np.int64)
    palette, inverse = np.unique(quantised, axis=0, return_inverse=True)
    return inverse.reshape(-1).astype(np.float64), palette.tolist()


def _pad(blob: bytes, fill: bytes = b"\x00") -> bytes:
    return blob + fill * ((4 - len(blob) % 4) % 4)


def write_glb(
    path: Path,
    positions: np.ndarray,
    triangles: np.ndarray | None,
    *,
    colors: np.ndarray | None = None,
    fields: list[dict[str, Any]] | None = None,
    units: str = "mm",
    stage: str = "geometry",
    source: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write positions (+ triangles) as one .glb. ``triangles=None`` writes POINTS."""

    positions = np.asarray(positions, dtype=np.float64)
    if positions.ndim != 2 or positions.shape[1] < 3:
        raise GeometryError("positions must be N x 3")
    positions = positions[:, :3]
    if not np.isfinite(positions).all():
        raise GeometryError("positions contain NaN or infinite values")
    fields = list(fields or [])
    buffers: list[bytes] = []
    views: list[dict[str, Any]] = []
    accessors: list[dict[str, Any]] = []
    offset = 0

    def add(
        array: np.ndarray,
        kind: str,
        target: int | None = None,
        minmax: bool = False,
        component: int = FLOAT,
    ) -> int:
        nonlocal offset
        array = np.ascontiguousarray(
            array, dtype="<f4" if component == FLOAT else "<u4"
        )
        view: dict[str, Any] = {
            "buffer": 0,
            "byteOffset": offset,
            "byteLength": array.nbytes,
        }
        if target:
            view["target"] = target
        views.append(view)
        accessor: dict[str, Any] = {
            "bufferView": len(views) - 1,
            "componentType": component,
            "count": int(array.shape[0]),
            "type": kind,
        }
        if minmax:
            flat = array.reshape(array.shape[0], -1)
            accessor["min"] = [float(v) for v in flat.min(axis=0)]
            accessor["max"] = [float(v) for v in flat.max(axis=0)]
        accessors.append(accessor)
        blob = _pad(array.tobytes())
        buffers.append(blob)
        offset += len(blob)
        return len(accessors) - 1

    count = positions.shape[0]
    attributes = {
        "POSITION": add(positions, "VEC3", ARRAY_BUFFER, minmax=True),
        "_NODE": add(np.arange(count, dtype=np.float64), "SCALAR", ARRAY_BUFFER),
    }
    if colors is not None:
        attributes["COLOR_0"] = add(colors, "VEC3", ARRAY_BUFFER)
    primitive: dict[str, Any] = {
        "attributes": attributes,
        "mode": 4 if triangles is not None else 0,
    }
    if triangles is not None:
        primitive["indices"] = add(
            np.asarray(triangles).reshape(-1),
            "SCALAR",
            ELEMENT_ARRAY_BUFFER,
            component=UINT32,
        )
    field_meta = []
    for field in fields:
        values = np.asarray(field["values"], dtype=np.float64).reshape(-1)
        if values.shape[0] != count:
            raise GeometryError(
                f"field {field['name']} has {values.shape[0]} values for {count} vertices"
            )
        field_meta.append(
            {
                "name": field["name"],
                "label": field.get("label", field["name"]),
                "unit": field.get("unit", ""),
                "location": "node",
                "count": count,
                "frames": 1,
                "accessor": add(values, "SCALAR"),
                "min": float(np.nanmin(values)),
                "max": float(np.nanmax(values)),
            }
        )
    clio: dict[str, Any] = {
        "stage": stage,
        "topology": "surface" if triangles is not None else "points",
        "units": {"length": units},
        "source": source,
        "fields": field_meta,
        "frames": [],
        "counts": {
            "vertices": int(count),
            "triangles": len(triangles) if triangles is not None else 0,
            "nodes": int(count),
            "cells": 0,
        },
        "bounds": {
            "min": [float(v) for v in positions.min(axis=0)],
            "max": [float(v) for v in positions.max(axis=0)],
        },
    }
    if triangles is not None:
        # Only a triangle mesh satisfies the viewport contract.
        clio = {"contract": CONTRACT, **clio}
    if extra:
        clio.update(extra)
    gltf = {
        "asset": {"version": "2.0", "generator": "clio appl-core to_glb"},
        "scene": 0,
        "scenes": [{"nodes": [0], "extras": {"clio": clio}}],
        "nodes": [{"mesh": 0, "name": stage}],
        "meshes": [{"name": stage, "primitives": [primitive]}],
        "buffers": [{"byteLength": offset}],
        "bufferViews": views,
        "accessors": accessors,
    }
    json_chunk = _pad(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), b" ")
    bin_chunk = b"".join(buffers)
    total = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(struct.pack("<4sII", b"glTF", 2, total))
        handle.write(struct.pack("<I4s", len(json_chunk), b"JSON") + json_chunk)
        handle.write(struct.pack("<I4s", len(bin_chunk), b"BIN\x00") + bin_chunk)
    return clio


def read_glb_json(path: Path) -> dict[str, Any]:
    """Return the JSON chunk of a .glb file."""

    data = path.read_bytes()
    magic, version, _ = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2:
        raise GeometryError(f"{path.name}: not a glTF 2.0 binary")
    length, kind = struct.unpack_from("<I4s", data, 12)
    if kind != b"JSON":
        raise GeometryError(f"{path.name}: first chunk is not JSON")
    return json.loads(data[20 : 20 + length].decode("utf-8"))


def mesh_from_text(
    vertices: Path, faces: Path, colors: Path | None, index_base: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, dict[str, Any]]:
    """Load a vertices/faces/(colours) text triplet."""

    positions = load_text(vertices, 3)[:, :3]
    triangles, notes = triangulate(load_text(faces, 3), positions.shape[0], index_base)
    rgb = normalise_colors(load_text(colors, 3), positions.shape[0]) if colors else None
    return positions, triangles, rgb, notes


def load_ply(path: Path) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None]:
    """Load a .ply with trimesh; returns (positions, triangles or None, colours or None)."""

    try:
        import trimesh  # pyright: ignore[reportMissingImports]
    except ImportError as exc:
        raise GeometryError(
            "reading .ply needs trimesh: rerun with `--with trimesh`"
        ) from exc
    loaded = trimesh.load(path, process=False)
    positions = np.asarray(loaded.vertices, dtype=np.float64)
    faces = getattr(loaded, "faces", None)
    triangles = (
        np.asarray(faces, dtype=np.uint32) if faces is not None and len(faces) else None
    )
    colors = None
    visual = getattr(loaded, "visual", None)
    vertex_colors = (
        getattr(visual, "vertex_colors", None) if visual is not None else None
    )
    if vertex_colors is None and hasattr(loaded, "colors"):
        vertex_colors = loaded.colors
    if vertex_colors is not None and len(vertex_colors) == len(positions):
        colors = np.asarray(vertex_colors, dtype=np.float64)[:, :3] / 255.0
    return positions, triangles, colors


def load_points(path: Path) -> tuple[np.ndarray, np.ndarray | None]:
    """Load an x y z [r g b] text file or an ASCII .pcd."""

    if path.suffix.lower() == ".pcd":
        header: dict[str, list[str]] = {}
        with path.open("r", encoding="ascii", errors="replace") as handle:
            for line in handle:
                parts = line.split()
                if not parts or parts[0].startswith("#"):
                    continue
                header[parts[0].upper()] = parts[1:]
                if parts[0].upper() == "DATA":
                    break
            if header.get("DATA", [""])[0].lower() != "ascii":
                raise GeometryError("only ASCII .pcd is supported")
            fields = [name.lower() for name in header.get("FIELDS", [])]
            data = np.loadtxt(handle, dtype=np.float64, ndmin=2)
        try:
            xyz = data[:, [fields.index("x"), fields.index("y"), fields.index("z")]]
        except ValueError as exc:
            raise GeometryError(".pcd lacks x/y/z fields") from exc
        return xyz, None
    data = load_text(path, 3)
    colors = (
        normalise_colors(data[:, 3:6], data.shape[0]) if data.shape[1] >= 6 else None
    )
    return data[:, :3], colors


def _fields_for(
    colors: np.ndarray | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if colors is None:
        return [], {}
    ids, palette = segment_ids(colors)
    if len(palette) > MAX_SEGMENTS:
        # Continuous colour (e.g. photo texture), not a segmentation: no field.
        return [], {
            "segments": {
                "count": len(palette),
                "note": "too many distinct colours for a segment field",
            }
        }
    return (
        [
            {
                "name": "SEGMENT",
                "label": "Segment (distinct vertex colour)",
                "unit": "",
                "values": ids,
            }
        ],
        {"segments": {"count": len(palette), "palette_rgb255": palette}},
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    mesh = sub.add_parser("mesh", help="vertices/faces/(colours) text triplet")
    mesh.add_argument("--vertices", type=Path, required=True)
    mesh.add_argument("--faces", type=Path, required=True)
    mesh.add_argument("--colors", type=Path)
    mesh.add_argument("--index-base", choices=("auto", "0", "1"), default="auto")
    ply = sub.add_parser("ply", help=".ply mesh (needs trimesh)")
    ply.add_argument("input", type=Path)
    for name in ("points", "pcd"):
        points = sub.add_parser(
            name, help="point cloud (refused unless --allow-points)"
        )
        points.add_argument("input", type=Path)
    for command in (mesh, ply, sub.choices["points"], sub.choices["pcd"]):
        command.add_argument("-o", "--output", type=Path, required=True)
        command.add_argument(
            "--units",
            default="mm",
            help="length unit of the coordinates (as documented by the data)",
        )
        command.add_argument(
            "--stage", default="geometry", help="a short label for the view"
        )
        command.add_argument(
            "--allow-points",
            action="store_true",
            help="write a POINTS glb the mesh viewport cannot show",
        )
    info = sub.add_parser("info", help="print a .glb's metadata")
    info.add_argument("input", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "info":
            gltf = read_glb_json(args.input)
            print(
                json.dumps(
                    gltf.get("scenes", [{}])[0].get("extras", {}).get("clio", {}),
                    indent=2,
                )
            )
            return 0
        notes: dict[str, Any] = {}
        if args.command == "mesh":
            positions, triangles, colors, notes = mesh_from_text(
                args.vertices, args.faces, args.colors, args.index_base
            )
            source = args.vertices.name
        elif args.command == "ply":
            positions, triangles, colors = load_ply(args.input)
            source = args.input.name
        else:
            positions, colors = load_points(args.input)
            triangles = None
            source = args.input.name
        if triangles is None and not args.allow_points:
            print(
                "refused: this input has no faces. clio.mesh-viewport.v1 renders triangle meshes only; "
                "use the matching surface/mesh files, or pass --allow-points for a plain glTF POINTS file "
                "that the viewport cannot display.",
                file=sys.stderr,
            )
            return 3
        fields, extra = _fields_for(colors)
        if notes:
            extra = {**extra, "conversion": notes}
        clio = write_glb(
            args.output,
            positions,
            triangles,
            colors=colors,
            fields=fields,
            units=args.units,
            stage=args.stage,
            source=source,
            extra=extra,
        )
    except (GeometryError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {args.output}")
    print(json.dumps(clio, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
