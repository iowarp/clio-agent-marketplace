"""A parametric enclosure for a measured board: base, lid, fit checks, print files and a scene.

Copy this file to <project>/enclosure/enclosure.py and run it there:

    python enclosure.py                       # build, check, write everything
    python enclosure.py --explode 25          # the scene with the lid lifted 25 mm
    python enclosure.py --section y=-70       # the scene cut by the plane y = -70

It reads board-envelope.json (from board_envelope.py) and refuses one that was measured from
another STEP than BOARD_STEP, or that lists parts with no body. It writes base/lid STEP and STL,
enclosure.3mf, enclosure.glb (nodes: board, each reference, base, lid, standoff_N, pillar_N,
cutout_<ref>) and fit-report.json, and exits 1 when a fit check fails. Needs CadQuery 2.6+.
"""

from __future__ import annotations

# --- parameters (millimetres and degrees) -----------------------------------------------
ENVELOPE = "../board-envelope.json"
BOARD_STEP = ""  # the STEP the envelope was measured from; empty: the one it names
WALL = 2.0  # shell wall and floor thickness
CLEARANCE = 1.0  # gap from the shell to any part
CUTOUT_CLEARANCE = 0.5  # gap around a connector's opening, per side
LID_STYLE = "screws"  # "screws": lid pillars clamp the board, screws into the base standoffs
SCREW_DIAMETER = 3.0  # M3
SCREW_PILOT = 2.5  # pilot hole in a standoff for a self-tapping screw
SCREW_CLEARANCE_HOLE = 3.4
STANDOFF_DIAMETER = 6.5
MIN_STANDOFF_HEIGHT = 3.0
FILLET = 1.0  # outer edges of the lid top (a 45° chamfer when they print on the bed); 0: none
PRINT_ORIENTATION = {"base": "floor-down", "lid": "top-down"}
NOZZLE = 0.4
OVERHANG_LIMIT = 45.0
#: Plug bodies that must pass through a connector's opening, as (width, height) across the
#: entry direction; a connector not listed uses its mating face.
PLUGS: dict[str, tuple[float, float]] = {}
#: Keepouts (by their source reference) that get a window through the lid.
WINDOWS: list[str] = []
# -------------------------------------------------------------------------------------------

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import cadquery as cq  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # board_envelope.py sits beside this file


def _load_envelope() -> dict[str, Any]:
    path = (HERE / ENVELOPE).resolve()
    envelope = json.loads(path.read_text(encoding="utf-8"))
    if BOARD_STEP:
        step = Path(BOARD_STEP) if Path(BOARD_STEP).is_absolute() else HERE / BOARD_STEP
    else:  # recorded relative to the envelope's folder
        step = path.parent / envelope["source"]["step"]
    step = step.resolve()
    if not step.exists():
        raise SystemExit(f"The board STEP {step} is missing; export it and measure again.")
    digest = hashlib.sha256(step.read_bytes()).hexdigest()
    if digest != envelope["source"]["sha256"]:
        raise SystemExit(
            f"{path.name} was measured from another export of the board than {step.name}: "
            "measure again with board_envelope.py before building the case."
        )
    if envelope.get("missing_bodies"):
        raise SystemExit(
            "These parts have no 3D body, so the case cannot clear them: "
            + ", ".join(envelope["missing_bodies"])
        )
    envelope["_step"] = str(step)
    return envelope


def _outline_wire(outline: dict[str, Any]) -> cq.Wire:
    edges = []
    for seg in outline["segments"]:
        start = cq.Vector(*seg["start"], 0)
        end = cq.Vector(*seg["end"], 0)
        if seg["type"] == "arc" and "mid" in seg:
            edges.append(cq.Edge.makeThreePointArc(start, cq.Vector(*seg["mid"], 0), end))
        else:
            edges.append(cq.Edge.makeLine(start, end))
    try:
        return cq.Wire.assembleEdges(edges)
    except Exception:  # noqa: BLE001 - a curve the segments cannot rebuild: use the polygon
        points = [cq.Vector(x, y, 0) for x, y in outline["polygon"]]
        return cq.Wire.makePolygon(points, close=True)


def _prism(wire: cq.Wire, z0: float, height: float) -> cq.Solid:
    face = cq.Face.makeFromWires(wire)
    return cq.Solid.extrudeLinear(face, cq.Vector(0, 0, height)).translate(cq.Vector(0, 0, z0))


def _offset(wire: cq.Wire, distance: float) -> cq.Wire:
    return wire.offset2D(distance, "arc")[0]


def _cylinder(x: float, y: float, z0: float, height: float, diameter: float) -> cq.Solid:
    return cq.Solid.makeCylinder(diameter / 2, height, cq.Vector(x, y, z0))


def _box(xmin: float, ymin: float, zmin: float, xmax: float, ymax: float, zmax: float) -> cq.Solid:
    return cq.Solid.makeBox(xmax - xmin, ymax - ymin, zmax - zmin, cq.Vector(xmin, ymin, zmin))


class Case:
    def __init__(self, envelope: dict[str, Any]) -> None:
        self.env = envelope
        out = envelope["outline"]
        self.board_bottom = out["bottom_z"]
        self.board_top = out["top_z"]
        self.board = _outline_wire(out)
        self.cavity = _offset(self.board, CLEARANCE)
        self.outer = _offset(self.cavity, WALL)
        depth = envelope["bottom"]["max_depth"]
        standoff = max(MIN_STANDOFF_HEIGHT, depth + CLEARANCE)
        self.floor = self.board_bottom - standoff  # inner floor of the base
        self.base_bottom = self.floor - WALL
        self.split = self.board_top  # base walls rise to the board's top face
        self.ceiling = self.board_top + envelope["top"]["max_height"] + CLEARANCE
        self.lid_top = self.ceiling + WALL
        self.notes: list[str] = []
        self.holes = [h for h in envelope["holes"] if "diameter" in h and not h.get("plated")]
        self.holes = [h for h in self.holes if h["diameter"] >= SCREW_DIAMETER]

    # The parts of the case, kept separate for the scene and fused for printing.
    def shell_base(self) -> cq.Shape:
        outer = _prism(self.outer, self.base_bottom, self.split - self.base_bottom)
        inner = _prism(self.cavity, self.floor, self.split - self.floor + 1)
        return outer.cut(inner)

    def shell_lid(self) -> cq.Shape:
        outer = _prism(self.outer, self.split, self.lid_top - self.split)
        inner = _prism(self.cavity, self.split - 1, self.ceiling - self.split + 1)
        lid = outer.cut(inner)
        if FILLET > 0:
            on_bed = PRINT_ORIENTATION["lid"] == "top-down"
            try:
                edges = cq.Workplane().add(lid).edges(">Z")
                lid = (edges.chamfer(FILLET) if on_bed else edges.fillet(FILLET)).val()
                if on_bed:
                    self.notes.append(
                        "The lid's top edges print on the bed, so they are chamfered at 45° "
                        "instead of filleted (a fillet there is an overhang)."
                    )
            except Exception as exc:  # noqa: BLE001 - reported, the lid keeps sharp edges
                self.notes.append(f"The lid's top edges were not rounded ({exc}).")
        return lid

    def standoffs(self) -> list[cq.Shape]:
        found = []
        for hole in self.holes:
            post = _cylinder(hole["x"], hole["y"], self.floor, self.board_bottom - self.floor,
                             STANDOFF_DIAMETER)
            pilot = _cylinder(hole["x"], hole["y"], self.floor, self.board_bottom - self.floor + 1,
                              SCREW_PILOT)
            found.append(post.cut(pilot))
        return found

    def pillars(self) -> list[cq.Shape]:
        found = []
        for hole in self.holes:
            post = _cylinder(hole["x"], hole["y"], self.board_top, self.ceiling - self.board_top,
                             STANDOFF_DIAMETER)
            bore = _cylinder(hole["x"], hole["y"], self.board_top - 1,
                             self.lid_top - self.board_top + 2, SCREW_CLEARANCE_HOLE)
            found.append(post.cut(bore))
        return found

    def lid_screw_holes(self) -> cq.Shape | None:
        bores = [
            _cylinder(h["x"], h["y"], self.board_top - 1, self.lid_top - self.board_top + 2,
                      SCREW_CLEARANCE_HOLE)
            for h in self.holes
        ]
        if not bores:
            return None
        solid: cq.Shape = bores[0]
        for bore in bores[1:]:
            solid = solid.fuse(bore)
        return solid

    def openings(self) -> dict[str, cq.Shape]:
        """Each connector's opening through the wall, its mating face plus the clearance."""
        found: dict[str, cq.Shape] = {}
        reach = CLEARANCE + WALL + 5.0
        for ref, conn in self.env["connectors"].items():
            if not conn.get("edge"):
                continue
            rect, at, edge = conn["rectangle"], conn["face_at"], conn["edge"]
            c = CUTOUT_CLEARANCE
            zmin, zmax = rect["z"][0] - c, rect["z"][1] + c
            if "y" in rect:
                y0, y1 = rect["y"][0] - c, rect["y"][1] + c
                x0, x1 = (at - reach, at + 1.0) if edge == "-x" else (at - 1.0, at + reach)
            else:
                x0, x1 = rect["x"][0] - c, rect["x"][1] + c
                y0, y1 = (at - reach, at + 1.0) if edge == "-y" else (at - 1.0, at + reach)
            found[ref] = _box(x0, y0, zmin, x1, y1, zmax)
        return found

    def windows(self) -> list[cq.Shape]:
        found = []
        for keepout in self.env["keepouts"]:
            if keepout["source"] not in WINDOWS:
                continue
            points = [cq.Vector(x, y, 0) for x, y in keepout["polygon"]]
            wire = cq.Wire.makePolygon(points, close=True)
            found.append(_prism(wire, self.ceiling - 1, self.lid_top - self.ceiling + 2))
        return found

    def build(self) -> dict[str, Any]:
        base = self.shell_base()
        lid = self.shell_lid()
        openings = self.openings()
        for cut in openings.values():
            base = base.cut(cut)
            lid = lid.cut(cut)
        for window in self.windows():
            lid = lid.cut(window)
        bores = self.lid_screw_holes()
        if bores is not None:
            lid = lid.cut(bores)
        standoffs = self.standoffs()
        pillars = self.pillars()
        printed_base: cq.Shape = base
        for post in standoffs:
            printed_base = printed_base.fuse(post)
        printed_lid: cq.Shape = lid
        for post in pillars:
            printed_lid = printed_lid.fuse(post)
        return {
            "base": base,
            "lid": lid,
            "standoffs": standoffs,
            "pillars": pillars,
            "openings": openings,
            "printed_base": printed_base.clean(),
            "printed_lid": printed_lid.clean(),
        }


# --- fit checks ---------------------------------------------------------------------------


def _bodies(step: str) -> dict[str, cq.Shape]:
    from board_envelope import read_step  # noqa: PLC0415 - the measuring script, beside this one

    bodies = read_step(Path(step))
    named = {}
    for body in bodies:
        name = body.name if body.name and not body.name.startswith("=>") else "pcb"
        named[name] = body.shape
    return named


def _overhangs(shape: cq.Shape, orientation: str) -> list[dict[str, Any]]:
    """Faces that hang beyond the limit in the print orientation (curved faces sampled)."""
    flip = orientation == "top-down"
    plate = shape.BoundingBox().zmax if flip else shape.BoundingBox().zmin
    limit = math.sin(math.radians(OVERHANG_LIMIT + 0.5))
    found = []
    for face in shape.Faces():
        if face.Area() < 0.5:
            continue
        samples = [(0.5, 0.5)] if face.geomType() == "PLANE" else [
            (u / 4, v / 4) for u in range(5) for v in range(5)
        ]
        worst = -1.0
        where = face.Center()
        for u, v in samples:
            try:
                point = face.positionAt(u, v)
                normal = face.normalAt(point)
            except Exception:  # noqa: BLE001 - a trimmed sample off the face
                continue
            if abs(point.z - plate) < 0.05:
                continue  # resting on the bed
            down = normal.z if flip else -normal.z
            if down > worst:
                worst, where = down, point
        if worst > limit:
            found.append(
                {
                    "at": [round(where.x, 2), round(where.y, 2), round(where.z, 2)],
                    "angle_from_vertical": round(math.degrees(math.asin(min(1.0, worst))), 1),
                    "area_mm2": round(face.Area(), 1),
                }
            )
    return found


def _outer_face(case: Case, edge: str, across: float, z: float) -> float | None:
    """Where the case's outer surface is, along the connector's edge, in front of its face."""
    bb = case.outer.BoundingBox()
    del across, z  # the outline's extreme on that side is the wall's outer face there
    return {"-x": bb.xmin, "+x": bb.xmax, "-y": bb.ymin, "+y": bb.ymax}.get(edge)


def _box_gap(a: cq.Shape, b: cq.Shape) -> float:
    """The gap between the two shapes' bounding boxes: the shapes are never closer."""
    p, q = a.BoundingBox(), b.BoundingBox()
    dx = max(0.0, q.xmin - p.xmax, p.xmin - q.xmax)
    dy = max(0.0, q.ymin - p.ymax, p.ymin - q.ymax)
    dz = max(0.0, q.zmin - p.zmax, p.zmin - q.zmax)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _gap(a: cq.Shape, b: cq.Shape) -> tuple[float, str]:
    """The distance between two shapes, and how it was found.

    OCC's ``Shape.distance`` has returned 0.0 for a pair 25 mm apart (ledger FN-7). The
    bounding boxes' gap is a lower bound on the true distance, so a smaller distance is
    wrong; the bound is used instead, which can only under-report the clearance.
    """
    measured = a.distance(b)
    bound = _box_gap(a, b)
    if measured < bound - 1e-6:
        return bound, "bounding boxes (Shape.distance gave less)"
    return measured, "Shape.distance"


def fit_checks(case: Case, made: dict[str, Any], bodies: dict[str, cq.Shape]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, **detail: Any) -> None:
        checks.append({"check": name, "passed": bool(passed), **detail})

    shells = {"base": made["printed_base"], "lid": made["printed_lid"]}
    # Each element of the case by the name the scene gives it, so a failure says which one.
    elements = {"base": made["base"], "lid": made["lid"]}
    elements.update({f"standoff_{i}": p for i, p in enumerate(made["standoffs"], start=1)})
    elements.update({f"pillar_{i}": p for i, p in enumerate(made["pillars"], start=1)})
    connectors = set(made["openings"])
    for ref, body in sorted(bodies.items()):
        if ref == "pcb" or ref in connectors:
            continue  # a connector reaches into its opening; checked below
        for element, shape in elements.items():
            gap, method = _gap(body, shape)
            if gap < CLEARANCE - 0.05:
                check("clearance", False, part=ref, element=element, gap=round(gap, 2),
                      required=CLEARANCE, measured_by=method)
    if not any(c["check"] == "clearance" for c in checks):
        check("clearance", True, required=CLEARANCE)

    for index, (hole, post) in enumerate(zip(case.holes, made["standoffs"], strict=True), start=1):
        center = post.Center()
        offset = math.dist((center.x, center.y), (hole["x"], hole["y"]))
        check("standoff_axis", offset < 0.05, standoff=f"standoff_{index}",
              hole=[hole["x"], hole["y"]], offset=round(offset, 3))
    if not case.holes:
        check("standoff_axis", False, note="no mounting hole of the screw's size was measured")

    for ref, conn in case.env["connectors"].items():
        if ref not in made["openings"]:
            continue
        rect, at, edge = conn["rectangle"], conn["face_at"], conn["edge"]
        width, height = PLUGS.get(ref, (None, None))
        across = "y" if "y" in rect else "x"
        span = rect[across]
        mid = (span[0] + span[1]) / 2
        zmid = (rect["z"][0] + rect["z"][1]) / 2
        w = width if width else span[1] - span[0]
        h = height if height else rect["z"][1] - rect["z"][0]
        travel = CLEARANCE + WALL + 10.0
        if across == "y":
            x0, x1 = (at - travel, at) if edge == "-x" else (at, at + travel)
            plug = _box(x0, mid - w / 2, zmid - h / 2, x1, mid + w / 2, zmid + h / 2)
        else:
            y0, y1 = (at - travel, at) if edge == "-y" else (at, at + travel)
            plug = _box(mid - w / 2, y0, zmid - h / 2, mid + w / 2, y1, zmid + h / 2)
        touching = {name: shell.intersect(plug).Volume() for name, shell in shells.items()}
        gap = min(_gap(plug, shell)[0] for shell in shells.values())
        outer_face = _outer_face(case, edge, mid, zmid)
        recess = abs(outer_face - at) if outer_face is not None else None
        check("cutout", all(v < 1e-6 for v in touching.values()), connector=f"cutout_{ref}",
              plug=[round(w, 2), round(h, 2)], gap=round(gap, 2),
              touches=[n for n, v in touching.items() if v >= 1e-6],
              recess=round(recess, 2) if recess is not None else None)

    top_gap = case.ceiling - (case.board_top + case.env["top"]["max_height"])
    check("lid_clears_top", top_gap >= CLEARANCE - 1e-6, part=case.env["top"]["part"],
          gap=round(top_gap, 2))
    bottom_gap = (case.board_bottom - case.env["bottom"]["max_depth"]) - case.floor
    check("base_clears_bottom", bottom_gap >= CLEARANCE - 1e-6 or not case.env["bottom"]["part"],
          part=case.env["bottom"]["part"], gap=round(bottom_gap, 2))

    check("wall_printable", WALL >= 2 * NOZZLE, wall=WALL, minimum=2 * NOZZLE)
    for name in ("base", "lid"):
        found = _overhangs(made[f"printed_{name}"], PRINT_ORIENTATION[name])
        check("overhangs", not found, part=name, orientation=PRINT_ORIENTATION[name],
              limit=OVERHANG_LIMIT, places=found[:20], count=len(found))

    return {
        "passed": all(c["passed"] for c in checks),
        "parameters": {
            "wall": WALL, "clearance": CLEARANCE, "cutout_clearance": CUTOUT_CLEARANCE,
            "lid_style": LID_STYLE, "screw": SCREW_DIAMETER, "nozzle": NOZZLE,
            "overhang_limit": OVERHANG_LIMIT, "plugs": PLUGS, "windows": WINDOWS,
        },
        "envelope": case.env["source"],
        "checks": checks,
        "notes": case.notes,
    }


# --- outputs ------------------------------------------------------------------------------


def scene(case: Case, made: dict[str, Any], bodies: dict[str, cq.Shape], *, lift: float = 0.0,
          section: tuple[str, float] | None = None) -> cq.Assembly:
    def cut(shape: cq.Shape) -> cq.Shape | None:
        """Keep the half of a shape on the low side of the section plane."""
        if not section:
            return shape
        axis, value = section
        big = 1e4
        low = [-big, -big, -big]
        high = [big, big, big]
        high["xyz".index(axis)] = value
        part = shape.intersect(_box(*low, *high))
        return part if part.Volume() > 1e-9 else None

    up = cq.Location(cq.Vector(0, 0, lift))
    assy = cq.Assembly(name="enclosure")
    board = cq.Assembly(name="board")
    for name, shape in sorted(bodies.items()):
        piece = cut(shape)
        if piece is not None:
            board.add(piece, name=name, color=cq.Color(0.1, 0.45, 0.2) if name == "pcb" else None)
    assy.add(board, name="board")
    shell = cq.Color(0.82, 0.84, 0.88)
    # The wall around each opening is its own node (cutout_<ref>), carved out of the base
    # and lid here so no two nodes share a surface.
    frames = {ref: _grow(opening, 1.5) for ref, opening in made["openings"].items()}
    for name, shape, loc in (("base", made["base"], None), ("lid", made["lid"], up)):
        for frame in frames.values():
            shape = shape.cut(frame)
        piece = cut(shape)
        if piece is not None:
            assy.add(piece, name=name, color=shell, loc=loc)
    for index, post in enumerate(made["standoffs"], start=1):
        piece = cut(post)
        if piece is not None:
            assy.add(piece, name=f"standoff_{index}", color=shell)
    for index, post in enumerate(made["pillars"], start=1):
        piece = cut(post)
        if piece is not None:
            assy.add(piece, name=f"pillar_{index}", color=shell, loc=up)
    for ref, frame in frames.items():
        # The wall around the opening, so a mark on it names the cutout; the lid's share
        # moves with the lid.
        for part, shape, loc in (("base", made["base"], None), ("lid", made["lid"], up)):
            ring = shape.intersect(frame)
            piece = cut(ring) if ring.Volume() > 1e-9 else None
            if piece is not None:
                suffix = "" if part == "base" else "_lid"
                assy.add(piece, name=f"cutout_{ref}{suffix}", color=shell, loc=loc)
    return assy


def _grow(box: cq.Shape, by: float) -> cq.Shape:
    bb = box.BoundingBox()
    return _box(bb.xmin - by, bb.ymin - by, bb.zmin - by, bb.xmax + by, bb.ymax + by, bb.zmax + by)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and check the enclosure.")
    parser.add_argument("--explode", type=float, default=0.0, help="lift the lid by this many mm")
    parser.add_argument("--section", default="", help="cut the scene, e.g. y=-70 or x=80")
    args = parser.parse_args(argv)
    envelope = _load_envelope()
    case = Case(envelope)
    made = case.build()
    bodies = _bodies(envelope["_step"])
    out = HERE
    cq.exporters.export(made["printed_base"], str(out / "base.step"))
    cq.exporters.export(made["printed_lid"], str(out / "lid.step"))
    cq.exporters.export(made["printed_base"], str(out / "base.stl"), tolerance=0.02)
    cq.exporters.export(made["printed_lid"], str(out / "lid.stl"), tolerance=0.02)
    try:
        both = cq.Compound.makeCompound([made["printed_base"], made["printed_lid"]])
        cq.exporters.export(both, str(out / "enclosure.3mf"), exportType="3MF", tolerance=0.02)
    except Exception as exc:  # noqa: BLE001 - reported; the STL files are there either way
        case.notes.append(f"enclosure.3mf was not written ({exc}); use the STL files.")
    report = fit_checks(case, made, bodies)
    section = None
    if args.section:
        axis, _, value = args.section.partition("=")
        section = (axis.strip().lower(), float(value))
    name = "enclosure"
    if args.explode:
        name += "-exploded"
    if section:
        name += f"-section-{section[0]}"
    assembled = scene(case, made, bodies, lift=args.explode, section=section)
    save = getattr(assembled, "export", None) or assembled.save
    save(str(out / f"{name}.glb"))
    report["scene"] = f"{name}.glb"
    (out / "fit-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    failed = [c for c in report["checks"] if not c["passed"]]
    print(f"Wrote base/lid STEP and STL, enclosure.3mf, {name}.glb and fit-report.json.")
    print("All fit checks pass." if not failed else f"{len(failed)} fit check(s) failed:")
    for c in failed:
        print("- " + json.dumps(c))
    for note in case.notes:
        print("Note: " + note)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
