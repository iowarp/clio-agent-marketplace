---
name: pcb-pipeline
description: The whole path from a board brief to a board house package with the KiCad connector in CLIO, which connector and skill covers each stage, the views and the workbench, and how placement passes can be kept as a study.
---

# From a brief to a board

The KiCad connector's tools place, route and check a board; the person watches and steers
through the views.

## KiCad itself

The connector attaches to a running KiCad or starts one (headless where KiCad 11 allows, else
on a virtual display). `kicad_session_status` says which, or what is missing. `install-kicad`
covers finding a KiCad elsewhere on the machine and installing one.

## The stages, and what covers each

- **Brief and enclosure.** An enclosure designed elsewhere (Fusion) gives its board outline as
  a DXF with the mounting holes.
- **Parts.** `part-sourcing`: search by spec, what the catalogs' answers mean, catalog keys
  through a card, and scarce core parts.
- **Datasheets.** `lib_get_datasheet_url` fetches an IC's datasheet; `datasheet-pin-check`
  compares its pin table with the symbol and footprint, the one error ERC and DRC cannot see.
- **Schematic and ERC.** `run_erc` checks the schematic's electrical rules. It does not see a
  wire on the wrong pin or a label on the wrong net; the schematic view shows those.
- **Simulation.** Power stages and filters simulate on the spice connector, from
  `export_spice_netlist`; this connector does not simulate. `offer_plugin` with plugin `spice`
  offers it when it is not on, and its `install-simulator` skill covers a machine with no
  simulator. A regulator used exactly as its datasheet's reference circuit has little to
  simulate; without simulation, a power stage or filter's behaviour is unverified.
- **Outline and holes.** `pcb_import_outline_dxf` draws the enclosure's outline and holes;
  `pcb_set_board_outline_shape` draws one from points; `pcb_add_mounting_holes` adds holes by
  pattern.
- **Placement**: `pcb-placement`, and the study below.
- **Routing**: `pcb-routing`, with DRC (`run_drc`).
- **Release.** DFM checks and the manufacturing package (`fabrication-output`). Checks pass on
  boards with a keepout in the wrong place or a connector set back from the edge; the board
  view shows those (`set_layers` and `focus` on the keepouts and edge connectors).
  `export_3d_render` is a picture for the person, not a review. The STEP (`export_step`) goes
  back to the enclosure for a fit check (`pcb-enclosure`).

## The views

Each opens in a tab and follows every edit, whoever made it. Each view has its own tools
(`focus`, `select`, `capture`, `describe_region`; the board view also `set_layers` and `show`),
and `look_at_view` shows what one shows now. Placement, holes and routes are judged in the
board view and the wiring in the schematic view; a 3D render hides them.

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

A view's own tools steer it: `focus` (a reference, a net or a point), `set_layers`,
`select_row`, `select`, `capture` (a PNG of the view now) and `describe_region`. `focus` also
shows the person what you are talking about.

**The workbench.** `references/pcb-workbench.json` is a dashboard of the board, BOM and checks
views together, with `PROJECT_FOLDER` for the project folder and `PLACEMENT_METRICS` for the
artifact of the placement metrics. Its three views share `/pcb/selection`: selecting a BOM row
highlights its footprints on the board, selecting a violation focuses the board on it, and
selecting a footprint selects its BOM row. The schematic opens in its own tab.

## Placement passes as a study

Placement passes compare well as experiments in the science log, each with its measured
values: unrouted connections and ratsnest length (`pcb_get_ratsnest`), DRC count and courtyard
overlaps (`run_drc`), and after routing, completion, vias and track length. The workbench chart
reads one row per pass (`pass`, `unrouted`, `ratsnest_mm`, `drc`, `vias`, `track_mm`) from the
placement metrics artifact. A capture of each pass shows what the numbers do not.
