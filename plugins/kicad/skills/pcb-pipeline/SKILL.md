---
name: pcb-pipeline
description: The whole path from a board brief to a board house package with the KiCad connector in CLIO, which connector does each step, when to open the views and the workbench, how to ask for part-catalog keys, and how placement passes become a study.
---

# From a brief to a board

You design the board yourself through the KiCad connector's tools: you place, route and
check. The person watches and steers through the views. Never hand placement or routing to
the person, and never use a service whose own AI lays the board out.

## KiCad itself

The connector attaches to a running KiCad or starts one (headless where KiCad 11 allows,
else on a virtual display). `kicad_session_status` says which, or what is missing. When
KiCad is not found, follow the `install-kicad` skill: it looks for a copy elsewhere on the
machine first; installing system software is the person's decision, so say what you will
run first.

## The path, and who does each step

1. **Brief and enclosure.** Read the brief. When an enclosure is designed elsewhere (Fusion),
   take its board outline as a DXF with the mounting holes.
2. **Parts.** Follow the `part-sourcing` skill: search by spec, what the catalogs' answers
   mean, asking for catalog keys through a card when a search failed, and asking the person
   when a core part is scarce.
3. **Datasheets.** For each IC, fetch the datasheet (`lib_get_datasheet_url`) and ingest it
   with the documents tools, so values come with a page. Run `datasheet-pin-check` before
   layout.
4. **Schematic and ERC.** Build the schematic, `run_erc` until it is clean or every finding is
   explained.
5. **Simulation.** Simulate power stages and filters on the spice connector, from
   `export_spice_netlist`; this connector does not simulate. When the spice connector is not
   on, offer it (`offer_plugin` with plugin `spice` and what you would simulate). When it finds
   no simulator, its plugin's `install-simulator` skill looks for one on the machine, then asks
   the person to use it, install one or skip simulation. A board with nothing to simulate (a
   regulator used exactly as its datasheet's reference circuit, no filters) may skip it, and
   your summary says so. Whenever simulation is skipped, the summary says what stays
   unverified.
6. **Outline and holes.** `pcb_import_outline_dxf` draws the enclosure's outline and holes;
   `pcb_set_board_outline_shape` draws one from points; `pcb_add_mounting_holes` adds holes by
   pattern.
7. **Placement**, as a study (below), with the `pcb-placement` skill.
8. **Routing**, with the `pcb-routing` skill; DRC until clean.
9. **Release.** DFM checks and the manufacturing package. Look at the board first in the board
   view (its `capture`, with `set_layers` and `focus` on the keepouts and edge connectors):
   checks pass on boards with a keepout in the wrong place or a connector set back from the
   edge. `export_3d_render` is a picture to show the person, not a review. Exporting the
   release package is the person's step: say it is ready and what it holds. Send the STEP (`export_step`) back to the
   enclosure for a fit check.

## The views

Each opens in a tab and follows every edit, whoever made it. They are also how you review your
own work: each view has its own tools (`focus`, `select`, `capture`, `describe_region`; the
board view also `set_layers` and `show`), and `look_at_view` shows you what one shows now. Judge
placement, holes and routes in the board view and the wiring in the schematic view, not from a
3D render:

| Tool | Shows | The person can |
| --- | --- | --- |
| `view_board` | The board, layers, nets, 2D and 3D | drag, rotate, move to the other side, lock, highlight a net in KiCad, refill zones, run DRC |
| `view_schematic` | Every sheet | select symbols, mark one not fitted |
| `view_bom` | Parts with stock, price, lifecycle, datasheet, key specs | see alternates, choose one, mark not fitted, reprice |
| `view_checks` | DRC and ERC grouped by rule | select a violation, run again |
| `view_stackup` | Layers, materials, thicknesses, net classes | change a thickness and check the stackup |
| `view_parts` | A spec table with filters and compare | filter, compare, pick a part for a symbol |

What the person selects in a view reaches you as context with the kind, reference, net,
layer and position, so "move this closer to J1" names the part without asking. A mark the
person draws on a view arrives with the footprints, pads, tracks and nets under it.

You can steer a view with its own tools: `focus` (a reference, a net or a point),
`set_layers`, `select_row`, `select`, `capture` (a PNG of the view now) and
`describe_region`. Use `focus` to show the person what you are talking about.

**The workbench.** At the start of a design session, open the board, BOM and checks views
together in one dashboard from `references/pcb-workbench.json`: replace `PROJECT_FOLDER` with
the project folder and `PLACEMENT_METRICS` with the artifact of the placement metrics. Its
three views share `/pcb/selection`: selecting a BOM row highlights its footprints on the
board, selecting a violation focuses the board on it, and selecting a footprint selects its
BOM row. The schematic opens in its own tab.

## Placement passes are a study

Record each placement pass in the science log as an experiment with its measured values:
unrouted connections and ratsnest length (`pcb_get_ratsnest`), DRC count and courtyard
overlaps (`run_drc`), and after routing, completion, vias and track length. Compare passes
with your own code from those values. Write one row per pass (`pass`, `unrouted`,
`ratsnest_mm`, `drc`, `vias`, `track_mm`) to the placement metrics artifact the workbench
chart reads. A pass you call better cites the capture you looked at.
