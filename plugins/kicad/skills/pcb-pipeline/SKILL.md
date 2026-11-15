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
KiCad is not installed, follow the `install-kicad` skill; installing system software is the
person's decision, so say what you will run first.

## The path, and who does each step

1. **Brief and enclosure.** Read the brief. When an enclosure is designed elsewhere (Fusion),
   take its board outline as a DXF with the mounting holes.
2. **Parts.** Search by spec, not by guessing a part number: `lib_search_parametric` with
   filters (`{name, op, value, unit}`; values compare in SI units). Read one part's full sheet
   with `lib_get_component_specs`; put candidates side by side with `lib_compare_parts`.
   Open `view_parts` with your shortlist in `candidates` when the person should choose; their
   pick binds the part (`lib_bind_part_to_symbol`) and arrives as context.

   **When a part is scarce.** Stock is what the sources that answered report, not what exists:
   "out of stock at jlcsearch" means only that. A passive or other part with many equivalents
   is yours to swap for an in-stock one; say what you chose. A core part, one the design is
   built around (the processor or module, a sensor the brief names, the regulator, the
   connectors), that is out of stock, or stocked below what the build needs, is the person's
   decision: they know whether they can wait, pay more or redesign. Ask once with `ask_user`
   (a choice), saying which sources you asked and what each reported, and offer what is open:
   - add a part catalog (Nexar, DigiKey, Mouser), which you then raise with `offer_plugin`;
   - keep the part and order it when it is back, accepting the wait;
   - search further: other packages, pin-compatible parts, other families, or a part with no
     KiCad symbol (generate it from the datasheet, `datasheet-pin-check`);
   - change the requirement (another kind of sensor, another module).
   Carry on with work the answer does not change while you wait.
3. **Datasheets.** For each IC, fetch the datasheet (`lib_get_datasheet_url`) and ingest it
   with the documents tools, so values come with a page. Run `datasheet-pin-check` before
   layout.
4. **Schematic and ERC.** Build the schematic, `run_erc` until it is clean or every finding is
   explained.
5. **Simulation.** Simulate power stages and filters on the spice connector, from
   `export_spice_netlist`; this connector does not simulate.
6. **Outline and holes.** `pcb_import_outline_dxf` draws the enclosure's outline and holes;
   `pcb_set_board_outline_shape` draws one from points; `pcb_add_mounting_holes` adds holes by
   pattern.
7. **Placement**, as a study (below), with the `pcb-placement` skill.
8. **Routing**, with the `pcb-routing` skill; DRC until clean.
9. **Release.** DFM checks and the manufacturing package. Exporting the release package is the
   person's step: say it is ready and what it holds. Send the STEP (`export_step`) back to the
   enclosure for a fit check.

## The views

Each opens in a tab and follows every edit, whoever made it:

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

## Part catalogs and keys

Parts search uses jlcsearch (JLCPCB's catalog, no key) unless the person added keys for
Nexar, DigiKey or Mouser. Every sourcing result names the sources that answered. When one
says a search failed or hit a limit and lists sources that could be configured, and a key
would change the answer, ask once: `offer_plugin` with plugin `kicad`, your reason, and
`needs` set to the keys of the sources you want (the listing's `optional_needs` names them).
The person types keys into the card, never into the chat; never ask for a key in a message.
If they choose Not now, carry on with what jlcsearch gives and say what is missing; do not
ask again for the same keys in this conversation.

## Placement passes are a study

Record each placement pass in the science log as an experiment with its measured values:
unrouted connections and ratsnest length (`pcb_get_ratsnest`), DRC count and courtyard
overlaps (`run_drc`), and after routing, completion, vias and track length. Compare passes
with your own code from those values. Write one row per pass (`pass`, `unrouted`,
`ratsnest_mm`, `drc`, `vias`, `track_mm`) to the placement metrics artifact the workbench
chart reads. A pass you call better cites the capture you looked at.
