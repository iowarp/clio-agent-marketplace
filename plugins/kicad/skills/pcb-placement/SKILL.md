---
name: pcb-placement
description: Place a KiCad board's footprints with KiCad MCP Pro, from mechanical constraints to decoupling, and judge each placement pass by measured numbers and a look at the board.
---

# PCB placement

Use this skill to place or re-place the footprints of a KiCad board. Every move is a tool
call committed by the live KiCad (`pcb_move_footprint`, `pcb_set_footprint_layer`,
`pcb_set_footprint_locked`); never edit the board file by hand.

## Order

1. **Fix what the enclosure fixes.** Draw the outline first (`pcb_import_outline_dxf` from
   the enclosure's DXF, or `pcb_set_board_outline_shape`), then the mounting holes, then the
   connectors, switches, LEDs and anything that must line up with an opening. Lock each
   (`pcb_set_footprint_locked`) so later passes cannot move it. Add keepouts
   (`pcb_set_keepout_zone`) under antennas and around holes. An antenna keepout covers the
   antenna area the module's footprint marks (the part of its courtyard beyond the body), on
   every copper layer, at the module's position as placed: take its corners from the
   footprint, not from the body outline.
2. **Group by function from the schematic.** Read the hierarchy and the nets
   (`sch_get_*`, `pcb_get_ratsnest`): the power stage, the MCU and its crystal, each
   interface. Keep each group together and near the connector it serves.
3. **ICs, then their decoupling.** Place each IC, then its decoupling capacitors as close to
   the supply pins as its datasheet asks, on the same side, with the shortest loop to ground.
   Crystals sit next to their pins with no signals under them.
4. **Then the rest**: pull-ups, LEDs, test points.

`pcb_auto_place_by_schematic` and `pcb_auto_place_force_directed` give a first spread; use
them only as a seed, never as the answer.

## Judge a pass by numbers and by eye

After each pass, measure and record:

- unconnected connections and total ratsnest length (`pcb_get_ratsnest`);
- DRC violations, and courtyard overlaps among them (`run_drc`);
- after routing: completion, vias and track length.

Then look: the board view's `capture` (its app tool), or `pcb_visual_qa`. A pass is better only when the
numbers and the picture agree; say which capture you looked at. Do not call a pass better
because one number moved.

## Moving one part

`pcb_move_footprint(reference, x_mm, y_mm, rotation_deg)` keeps the angle unless you give
one. A footprint that is locked does not move; unlock it first if the person agrees.
`pcb_set_footprint_layer(reference, "B_Cu")` moves it to the back.
