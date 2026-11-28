---
name: pcb-placement
description: Place a KiCad board's footprints with KiCad MCP Pro, from mechanical constraints to decoupling, and judge a placement pass by measured numbers and a look at the board.
---

# PCB placement

Moves go through the live KiCad, which holds the open board (`pcb_move_footprint`,
`pcb_set_footprint_layer`, `pcb_set_footprint_locked`); an edit to the board file underneath
it is not what KiCad has open.

## What constrains a placement

- **The enclosure.** The outline (`pcb_import_outline_dxf` from the enclosure's DXF, or
  `pcb_set_board_outline_shape`), the mounting holes, and the connectors, switches and LEDs
  that line up with an opening are fixed by the case. A locked footprint
  (`pcb_set_footprint_locked`) stays where it is through later passes until it is unlocked.
- **Keepouts** (`pcb_set_keepout_zone`) under antennas and around holes. An antenna keepout
  covers the antenna area the module's footprint marks (the part of its courtyard beyond the
  body), on every copper layer, at the module's position as placed: its corners come from the
  footprint, not from the body outline.
- **Function.** The hierarchy and the nets (`sch_get_*`, `pcb_get_ratsnest`) group the parts:
  the power stage, the MCU and its crystal, each interface. A group kept together near the
  connector it serves keeps its nets short.
- **Decoupling.** A decoupling capacitor works as well as its loop is short: as close to the
  supply pins as the IC's datasheet asks, on the same side, with the shortest loop to ground.
  Crystals sit next to their pins with no signals under them.
- **The rest** (pull-ups, LEDs, test points) has the most freedom.

`pcb_auto_place_by_schematic` and `pcb_auto_place_force_directed` give a first spread that
knows none of the above.

## Judging a pass

The numbers of a pass:

- unconnected connections and total ratsnest length (`pcb_get_ratsnest`);
- DRC violations, and courtyard overlaps among them (`run_drc`);
- after routing: completion, vias and track length.

The picture: the board view's `capture` (its app tool), or `pcb_visual_qa`. One number moving
can hide a worse board; a pass is better when the numbers and the picture agree.

## Moving one part

`pcb_move_footprint(reference, x_mm, y_mm, rotation_deg)` keeps the angle unless given one. A
locked footprint does not move. `pcb_set_footprint_layer(reference, "B_Cu")` moves it to the
back.
