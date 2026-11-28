---
name: pcb-enclosure
description: "Design a 3D-printable case around a KiCad board: measure the board's STEP, build a parametric CadQuery enclosure with its fit checks, look at it in CLIO's 3D view, and hand over STEP, STL and 3MF."
---

# A case for a board

The case is a CadQuery program kept in the project, with its parameters at the top: a board
revision means running it again, not editing a mesh. Every number it uses comes from the
board's STEP; a component height or hole position typed from memory or a picture is how a case
misses its board.

A project that already has `board_envelope.py` and `enclosure.py` keeps its own copies, which do
not get this skill's later checks. Each carries a `SCRIPT_VERSION`; a copy older than this
skill's `scripts/` (or with none) lacks checks that keep the case true to the board. The
project's choices live in the parameter block at the top of `enclosure.py`, which carries over
to a newer copy. When the current scripts refuse an envelope, the case they would build fits
another board than the person's.

## 1. Every part needs a body

The board's STEP (`export_step`) names each footprint whose 3D model KiCad could not find; the
enclosure cannot clear a part it cannot see. `pcb-footprints` (bodies) covers giving each one a
body: KiCad's model when its 3D library has it, else an envelope body from the datasheet's
maximum dimensions. When no footprint resolves a model, KiCad's 3D library is probably not
installed; fetching only the models this board names into the project avoids a system install.

## 2. Measure

`scripts/board_envelope.py` and `scripts/enclosure.py` run from `<project>/enclosure/` and need
CadQuery. The first line of `lib_list_footprint_families` names Library Tools' Python and says
whether it has CadQuery, e.g. `<that python> board_envelope.py ../BOARD.step --pcb ../BOARD.kicad_pcb --out ../board-envelope.json`.
`uv run --no-project --with cadquery python …` also works, at about 1.7 GB downloaded into the
conversation's own cache each time.
It writes the outline (lines and arcs), the holes, each part's box and side, the connectors with
the board edge their plug enters from, the keepouts, and `missing_bodies` (exit 3 while any).

The record can be wrong for a board the script does not fully rebuild (an outline it does not
rebuild, a connector it does not find at an edge); the outline's size, the holes and the tallest
part compare against the board file. CadQuery on the STEP can write the same record by hand.

## 3. Build and check

`python enclosure.py` in `enclosure/` builds it. It refuses an envelope measured from another export
of the board (measure again) or with missing bodies. It writes `base.step`, `lid.step`, their
STL, `enclosure.3mf`, `enclosure.glb` and `fit-report.json`, and exits 1 when a check fails:

- **clearance**: the board and every part at least `CLEARANCE` from every element of the case,
  and never under `FIT_GAP` (the gap a print needs to go together), named;
- **standoff_axis**: each standoff on its hole;
- **cutout**: a plug of the connector's size passes through its opening; `recess` is how far the
  connector's face sits behind the case's outer surface, against the plug's datasheet (how far
  its contacts reach beyond its body); `PLUGS[ref]` sets the body's size for a plug whose body
  must enter the opening;
- **lid_clears_top**, **base_clears_bottom**, **wall_printable**, **overhangs** (with places).

A failing check names the part, the element and the distance; the parameters at the top of
`enclosure.py` change it. Defaults suit an FDM print in PLA or PETG (2 mm walls, 1 mm clearance,
0.5 mm around openings, M3 screws, 0.4 mm nozzle, 0.3 mm fit gap, 45° overhangs).

## 4. Look at it

Checks pass on cases that look wrong. `enclosure.glb`, registered as an artifact, shows in a
`clio.mesh-viewport.v1`; `nodeOpacity` for `base` and `lid` at about 0.3 lets the board show
through, so a capture shows whether the board sits on the standoffs, each opening lines up with
its connector and nothing pokes through a wall. `camera` takes `{"position": [x, y, z], "target": [x, y, z]}` in the view's own frame, which
is not the envelope's: the GLB is Y-up (the case's (x, y, z) in millimetres shows at
(x, z, -y)). Each capture reports that frame's `bounds` and every named part's centre
(`parts`, e.g. `cutout_J1 in enclosure`): a target at the part's centre and a position a few
tens of millimetres from it along the side you look from (`update_a2ui_components`) frames it.
`python enclosure.py --explode 40` writes an exploded case (`enclosure-exploded.glb`), and
`--section y=VALUE` a section through a tight fit (it keeps the side below the plane).

The scene's nodes are `board` (each part by its reference, `pcb` for the board), `base`, `lid`,
`standoff_N`, `pillar_N` and `cutout_<ref>` (`cutout_<ref>_lid` for the lid's share). A mark the
person draws over the case names them: "make this opening bigger" over `cutout_J1` means
`CUTOUT_CLEARANCE` or `PLUGS["J1"]`.

## 5. A board revision

A changed board needs a new STEP and envelope; `enclosure.py`'s parameters carry over, and the
new `fit-report.json` against the previous one shows what changed.

## Hand-over

The person prints the case: STEP to keep, STL and 3MF for the slicer, in `enclosure/`. Slicing,
printing and structural or thermal analysis are theirs.
