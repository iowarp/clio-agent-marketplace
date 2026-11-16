---
name: pcb-enclosure
description: "Design a 3D-printable case around a KiCad board: measure the board's STEP, build a parametric CadQuery enclosure with its fit checks, look at it in CLIO's 3D view, and hand over STEP, STL and 3MF."
---

# A case for a board

The case is a CadQuery program kept in the project, with its parameters at the top: a board
revision means running it again, not editing a mesh. Every number it uses comes from the
board's STEP. Never type a component height or a hole position from memory or from a picture.

A project that already has `board_envelope.py` and `enclosure.py` keeps its own copies, which do
not get this skill's later checks. Before running them for any step, compare each copy's
`SCRIPT_VERSION` with this skill's `scripts/`: replace a copy with an older or no
`SCRIPT_VERSION` by this skill's, carrying the values of the project's parameter block (the top
of `enclosure.py`) over, and say that you did. An older copy lacks checks that keep the case true
to the board, so it is never a way round a refusal: when the current scripts refuse an envelope,
the case they would build fits another board than the person's, and the answer is to measure
again or to tell the person why it cannot be built yet.

## 1. Every part needs a body

Export the board's STEP (`export_step`). KiCad names each footprint whose 3D model it could not
find; the enclosure cannot clear a part it cannot see. For each one, follow `pcb-footprints`
(bodies): use KiCad's model when its 3D library has it, else build an envelope body from the
datasheet's maximum dimensions. When no footprint resolves a model, KiCad's 3D library is
probably not installed: installing system packages is the person's decision (ask, and say the
command), and fetching only the models this board names into the project is an alternative
you can do yourself. Export again until no part is missing.

## 2. Measure

Copy `scripts/board_envelope.py` and `scripts/enclosure.py` from this skill into
`<project>/enclosure/`. They need CadQuery. Call `lib_list_footprint_families` first: its
first line names Library Tools' Python and says whether it has CadQuery. Run the scripts with
that Python, e.g. `<that python> board_envelope.py ../BOARD.step --pcb ../BOARD.kicad_pcb --out ../board-envelope.json`.
Only when it has no CadQuery, `uv run --no-project --with cadquery python …` installs it, about
1.7 GB downloaded into this conversation's own cache each time.
It writes the outline (lines and arcs), the holes, each part's box and side, the connectors with
the board edge their plug enters from, the keepouts, and `missing_bodies` (exit 3 while any).

Check the record against the board before trusting it: the outline's size against the board
file, the holes against the mounting holes, the tallest part against what you know of the
parts. When the script cannot measure this board properly (an outline it does not rebuild, a
connector it does not find at an edge), measure it yourself from the STEP with CadQuery and
write the same record; say what you measured and how.

## 3. Build and check

Run `python enclosure.py` in `enclosure/`. It refuses an envelope measured from another export
of the board (measure again) or with missing bodies. It writes `base.step`, `lid.step`, their
STL, `enclosure.3mf`, `enclosure.glb` and `fit-report.json`, and exits 1 when a check fails:

- **clearance**: the board and every part at least `CLEARANCE` from every element of the case,
  and never under `FIT_GAP` (the gap a print needs to go together), named;
- **standoff_axis**: each standoff on its hole;
- **cutout**: a plug of the connector's size passes through its opening; `recess` is how far the
  connector's face sits behind the case's outer surface. Compare it with the plug's datasheet
  (how far its contacts reach beyond its body): when the plug's body must enter the opening,
  set `PLUGS[ref]` to the body's size;
- **lid_clears_top**, **base_clears_bottom**, **wall_printable**, **overhangs** (with places).

A failing check names the part, the element and the distance. Change a parameter at the top of
`enclosure.py` and run again; the run you show passes every check, or you say which check you
could not meet and why. Defaults suit an FDM print in PLA or PETG (2 mm walls, 1 mm clearance,
0.5 mm around openings, M3 screws, 0.4 mm nozzle, 0.3 mm fit gap, 45° overhangs).

## 4. Look at it

Checks pass on cases that look wrong. Register `enclosure.glb` as an artifact and show it in a
`clio.mesh-viewport.v1` with `nodeOpacity` for `base` and `lid` at about 0.3, so the board shows
through. Look at the view yourself (capture it): the board sits on the standoffs, each opening
lines up with its connector, nothing pokes through a wall. Also show the case exploded
(`python enclosure.py --explode 40` writes `enclosure-exploded.glb`) and, when a fit is tight, a
section through it (`--section y=VALUE` keeps the side below the plane; pick the plane through
the part in question). Say what you looked at and what you saw.

The scene's nodes are `board` (each part by its reference, `pcb` for the board), `base`, `lid`,
`standoff_N`, `pillar_N` and `cutout_<ref>` (`cutout_<ref>_lid` for the lid's share). A mark the
person draws over the case names them: "make this opening bigger" over `cutout_J1` means
`CUTOUT_CLEARANCE` or `PLUGS["J1"]`.

## 5. A board revision

When the board changes, export the STEP, measure again and run `enclosure.py` again: its
parameters carry over. Compare the new `fit-report.json` with the previous one and say what
changed.

## Hand-over

The person prints the case: STEP to keep, STL and 3MF for the slicer, in `enclosure/`. Slicing,
printing and structural or thermal analysis are theirs.
