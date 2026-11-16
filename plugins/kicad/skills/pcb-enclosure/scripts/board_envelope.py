"""Measure a board's STEP into board-envelope.json, the record an enclosure is built from.

Every number comes from the STEP: the board solid gives the outline (lines and arcs), the
holes and the thickness; each part's body gives its box and side. The KiCad board file is
read only to classify: which parts are connectors, where the keepout areas are, which holes
are plated, and which footprints have no body in the STEP (the enclosure must not start while
any part has none).

    python board_envelope.py BOARD.step --pcb BOARD.kicad_pcb [--out board-envelope.json]

Coordinates are the STEP's, in millimetres: the board's bottom face at z = board bottom, its
top at z = board top, x and y as KiCad exported them (KiCad's y axis is flipped). Needs
CadQuery (2.6 or later).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cadquery as cq
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label, TDF_LabelSequence
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool

CONNECTOR_PREFIXES = ("J", "P", "CN", "USB", "X")
EDGE_REACH_MM = 1.5  # a connector body within this of the outline faces that edge


# --- KiCad board file (classification only) ---------------------------------------------


def _sexp(text: str) -> list[Any]:
    tokens = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)
    stack: list[list[Any]] = [[]]
    for token in tokens:
        if token == "(":
            stack.append([])
        elif token == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(token[1:-1] if token.startswith('"') else token)
    return stack[0][0]


def _children(node: list[Any], name: str) -> list[list[Any]]:
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def _first(node: list[Any], name: str) -> list[Any] | None:
    found = _children(node, name)
    return found[0] if found else None


@dataclass
class Footprint:
    reference: str
    library: str
    x: float
    y: float
    rotation: float
    side: str
    model: bool
    keepouts: list[list[tuple[float, float]]] = field(default_factory=list)
    plated_holes: list[tuple[float, float, float]] = field(default_factory=list)


def _xy_list(poly: list[Any]) -> list[tuple[float, float]]:
    pts = _first(poly, "pts") or []
    return [(float(p[1]), float(p[2])) for p in _children(pts, "xy")]


def _keepout(zone: list[Any]) -> list[tuple[float, float]] | None:
    if _first(zone, "keepout") is None:
        return None
    poly = _first(zone, "polygon")
    return _xy_list(poly) if poly else None


def read_pcb(path: Path) -> tuple[list[Footprint], list[list[tuple[float, float]]]]:
    root = _sexp(path.read_text(encoding="utf-8"))
    footprints: list[Footprint] = []
    for fp in _children(root, "footprint"):
        at = _first(fp, "at") or ["at", 0, 0]
        x, y = float(at[1]), float(at[2])
        rot = float(at[3]) if len(at) > 3 else 0.0
        layer = (_first(fp, "layer") or ["layer", "F.Cu"])[1]
        reference = ""
        for prop in _children(fp, "property"):
            if len(prop) > 2 and prop[1] == "Reference":
                reference = prop[2]
        for text in _children(fp, "fp_text"):
            if len(text) > 2 and text[1] == "reference":
                reference = text[2]
        item = Footprint(
            reference=reference,
            library=str(fp[1]) if len(fp) > 1 and isinstance(fp[1], str) else "",
            x=x,
            y=y,
            rotation=rot,
            side="bottom" if layer.startswith("B.") else "top",
            model=bool(_children(fp, "model")),
        )
        cos, sin = math.cos(math.radians(-rot)), math.sin(math.radians(-rot))
        for zone in _children(fp, "zone"):
            local = _keepout(zone)
            if local:
                # KiCad stores a footprint's zones in board coordinates already.
                item.keepouts.append(local)
        for pad in _children(fp, "pad"):
            if len(pad) > 2 and pad[2] == "thru_hole":
                pat = _first(pad, "at") or ["at", 0, 0]
                drill = _first(pad, "drill")
                if drill and len(drill) > 1:
                    try:
                        diameter = float(drill[1])
                    except ValueError:
                        diameter = float(drill[2])
                    px, py = float(pat[1]), float(pat[2])
                    item.plated_holes.append(
                        (x + px * cos - py * sin, y + px * sin + py * cos, diameter)
                    )
        footprints.append(item)
    board_keepouts = [k for k in (_keepout(z) for z in _children(root, "zone")) if k]
    return footprints, board_keepouts


# --- STEP -------------------------------------------------------------------------------


@dataclass
class Body:
    name: str
    shape: cq.Shape
    tx: float
    ty: float

    @property
    def box(self) -> cq.BoundBox:
        return self.shape.BoundingBox()


def _name(label: TDF_Label) -> str:
    attr = TDataStd_Name()
    return attr.Get().ToExtString() if label.FindAttribute(TDataStd_Name.GetID_s(), attr) else ""


def read_step(path: Path) -> list[Body]:
    doc = TDocStd_Document(TCollection_ExtendedString("envelope"))
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    if reader.ReadFile(str(path)) != 1 or not reader.Transfer(doc):
        raise SystemExit(f"Could not read {path} as STEP.")
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    roots = TDF_LabelSequence()
    tool.GetFreeShapes(roots)
    bodies: list[Body] = []
    for i in range(1, roots.Length() + 1):
        components = TDF_LabelSequence()
        tool.GetComponents_s(roots.Value(i), components)
        for j in range(1, components.Length() + 1):
            label = components.Value(j)
            shape = tool.GetShape_s(label)
            move = tool.GetLocation_s(label).Transformation().TranslationPart()
            bodies.append(Body(_name(label), cq.Shape.cast(shape), move.X(), move.Y()))
    return bodies


def _board_body(bodies: list[Body]) -> Body:
    def score(body: Body) -> float:
        box = body.box
        return box.xlen * box.ylen if box.zlen < 4.0 else -1.0

    return max(bodies, key=score)


def _round(value: float) -> float:
    return round(value, 3)


def _edge_record(edge: cq.Edge) -> dict[str, Any]:
    start, end = edge.startPoint(), edge.endPoint()
    record: dict[str, Any] = {
        "type": "line" if edge.geomType() == "LINE" else "arc",
        "start": [_round(start.x), _round(start.y)],
        "end": [_round(end.x), _round(end.y)],
    }
    if edge.geomType() == "CIRCLE":
        center = edge.arcCenter()
        record["type"] = "arc"
        record["center"] = [_round(center.x), _round(center.y)]
        record["radius"] = _round(edge.radius())
        mid = edge.positionAt(0.5)
        record["mid"] = [_round(mid.x), _round(mid.y)]
    elif edge.geomType() != "LINE":
        record["type"] = "curve"
    return record


def _outline(board: Body) -> tuple[dict[str, Any], list[dict[str, Any]], cq.Face]:
    box = board.box
    tops = [
        f
        for f in board.shape.Faces()
        if f.geomType() == "PLANE"
        and abs(f.normalAt().z) > 0.99
        and abs(f.Center().z - box.zmax) < 0.05
    ]
    if not tops:
        raise SystemExit("The board body has no flat top face to read the outline from.")
    top = max(tops, key=lambda f: f.Area())
    outer = top.outerWire()
    points = [
        [_round(v.x), _round(v.y)] for v in outer.positions([i / 180 for i in range(181)])
    ]
    outline = {
        "segments": [_edge_record(e) for e in outer.Edges()],
        "polygon": points,
        "thickness": _round(box.zlen),
        "bottom_z": _round(box.zmin),
        "top_z": _round(box.zmax),
        "bounds": [_round(box.xmin), _round(box.ymin), _round(box.xmax), _round(box.ymax)],
    }
    holes = []
    for wire in top.innerWires():
        edges = wire.Edges()
        if len(edges) == 1 and edges[0].geomType() == "CIRCLE":
            center = edges[0].arcCenter()
            holes.append(
                {
                    "x": _round(center.x),
                    "y": _round(center.y),
                    "diameter": _round(2 * edges[0].radius()),
                }
            )
        else:
            wb = wire.BoundingBox()
            holes.append(
                {
                    "x": _round(wb.center.x),
                    "y": _round(wb.center.y),
                    "cutout": [_round(wb.xmin), _round(wb.ymin), _round(wb.xmax), _round(wb.ymax)],
                }
            )
    return outline, holes, top


def _pcb_to_step(footprints: list[Footprint], bodies: dict[str, Body]) -> tuple[float, float]:
    """KiCad exports x as is and y flipped; the offsets come from the parts present in both."""
    dx = [bodies[f.reference].tx - f.x for f in footprints if f.reference in bodies]
    dy = [bodies[f.reference].ty + f.y for f in footprints if f.reference in bodies]
    if not dx:
        return 0.0, 0.0
    return statistics.median(dx), statistics.median(dy)


def _connector(ref: str, footprint: Footprint | None) -> bool:
    if footprint and "connector" in footprint.library.lower():
        return True
    head = re.match(r"[A-Za-z]+", ref)
    return bool(head) and head.group(0).upper() in CONNECTOR_PREFIXES


def _mating_face(box: cq.BoundBox, bounds: list[float]) -> dict[str, Any] | None:
    xmin, ymin, xmax, ymax = bounds
    gaps = {
        "-x": box.xmin - xmin,
        "+x": xmax - box.xmax,
        "-y": box.ymin - ymin,
        "+y": ymax - box.ymax,
    }
    side, gap = min(gaps.items(), key=lambda item: item[1])
    if gap > EDGE_REACH_MM:
        return None
    axis = side[1]
    if axis == "x":
        face = {"y": [_round(box.ymin), _round(box.ymax)]}
        at = box.xmin if side == "-x" else box.xmax
    else:
        face = {"x": [_round(box.xmin), _round(box.xmax)]}
        at = box.ymin if side == "-y" else box.ymax
    face["z"] = [_round(box.zmin), _round(box.zmax)]
    return {
        "edge": side,
        "face_at": _round(at),
        "rectangle": face,
        "entry_direction": ("+" if side.startswith("-") else "-") + axis,
        "overhang": _round(-gap),
    }


def missing_bodies(by_ref: dict[str, Footprint], named: dict[str, Any]) -> list[str]:
    """Parts with no body in the STEP, or none in the board file (an older STEP may still
    hold a body the board no longer has): the case cannot be sized around them."""
    return sorted(
        ref
        for ref, footprint in by_ref.items()
        if ref and not ref.startswith("#") and (ref not in named or not footprint.model)
    )


def measure(step: Path, pcb: Path | None, revision: str) -> dict[str, Any]:
    if pcb is not None and pcb.exists() and pcb.stat().st_mtime > step.stat().st_mtime + 1:
        # The STEP shows the board as it was when exported; a later edit (a part moved, a
        # body removed) is not in it, so measuring it would describe another board.
        raise SystemExit(
            f"{step.name} is older than {pcb.name}: the board changed after the STEP was "
            "exported. Export the STEP again, then measure."
        )
    bodies = read_step(step)
    board = _board_body(bodies)
    named = {b.name: b for b in bodies if b is not board and b.name and not b.name.startswith("=>")}
    outline, holes, _top = _outline(board)
    footprints, board_keepouts = read_pcb(pcb) if pcb else ([], [])
    by_ref = {f.reference: f for f in footprints}
    dx, dy = _pcb_to_step(footprints, named)

    def to_step(x: float, y: float) -> list[float]:
        return [_round(x + dx), _round(-y + dy)]

    plated = [
        (to_step(hx, hy), d) for f in footprints for (hx, hy, d) in f.plated_holes
    ]
    for hole in holes:
        if "diameter" in hole:
            hole["plated"] = any(
                math.dist(p, (hole["x"], hole["y"])) < 0.2 and abs(d - hole["diameter"]) < 0.2
                for p, d in plated
            )

    top_z, bottom_z = outline["top_z"], outline["bottom_z"]
    parts: dict[str, Any] = {}
    connectors: dict[str, Any] = {}
    highest = {"top": (0.0, ""), "bottom": (0.0, "")}
    for ref, body in sorted(named.items()):
        box = body.box
        side = "bottom" if box.zmax <= bottom_z + 0.01 else "top"
        parts[ref] = {
            "side": side,
            "box": [_round(v) for v in (box.xmin, box.ymin, box.zmin, box.xmax, box.ymax, box.zmax)],
        }
        reach = box.zmax - top_z if side == "top" else bottom_z - box.zmin
        if reach > highest[side][0]:
            highest[side] = (reach, ref)
        if _connector(ref, by_ref.get(ref)):
            face = _mating_face(box, outline["bounds"])
            connectors[ref] = face or {"edge": None, "note": "not at a board edge"}

    keepouts = []
    for ref, fp in by_ref.items():
        for poly in fp.keepouts:
            keepouts.append({"source": ref, "polygon": [to_step(x, y) for x, y in poly]})
    for poly in board_keepouts:
        keepouts.append({"source": "board", "polygon": [to_step(x, y) for x, y in poly]})

    missing = missing_bodies(by_ref, named)
    return {
        "source": {
            "step": str(step),
            "sha256": hashlib.sha256(step.read_bytes()).hexdigest(),
            "revision": revision,
            "pcb": str(pcb) if pcb else "",
            "pcb_sha256": hashlib.sha256(pcb.read_bytes()).hexdigest() if pcb else "",
        },
        "units": "mm",
        "frame": "STEP coordinates as exported by KiCad (y flipped from the board file)",
        "outline": outline,
        "holes": holes,
        "top": {"max_height": _round(highest["top"][0]), "part": highest["top"][1]},
        "bottom": {"max_depth": _round(highest["bottom"][0]), "part": highest["bottom"][1]},
        "parts": parts,
        "connectors": connectors,
        "keepouts": keepouts,
        "missing_bodies": missing,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", type=Path)
    parser.add_argument("--pcb", type=Path)
    parser.add_argument("--out", type=Path, default=Path("board-envelope.json"))
    parser.add_argument("--revision", default="")
    args = parser.parse_args(argv)
    envelope = measure(args.step, args.pcb, args.revision)
    # Paths are kept relative to the envelope's folder, so the project stays movable.
    for key in ("step", "pcb"):
        value = envelope["source"][key]
        if value:
            envelope["source"][key] = os.path.relpath(Path(value).resolve(), args.out.resolve().parent)
    args.out.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}: {len(envelope['parts'])} parts, {len(envelope['holes'])} holes, "
          f"top {envelope['top']['max_height']} mm ({envelope['top']['part']}), "
          f"connectors {', '.join(envelope['connectors']) or 'none'}.")
    if envelope["missing_bodies"]:
        print("No 3D body in the STEP for: " + ", ".join(envelope["missing_bodies"]))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
