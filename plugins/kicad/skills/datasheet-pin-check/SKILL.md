---
name: datasheet-pin-check
description: Check an IC's, connector's or polarized part's symbol and footprint pin map against its datasheet's pin table, take values the distributors lack from the datasheet with the page cited, and build a missing symbol from the pin table.
---

# Datasheet pin check

A wrong pin map is the error no later check catches: ERC and DRC pass on a board whose
regulator's input and output are swapped. The datasheet's pin table is the only reference
that shows it, and a part laid out on a wrong map means a new board.

## What to compare, and the tools for it

- **The datasheet.** `lib_get_datasheet_url` (or the BOM's datasheet link) finds it; a PDF
  saved in the project folder reads with `view_pdf`, which gives the page each value is on.
- **The pin table** is per package: the same part in another package has another pin map.
- **The symbol's pins** (`sch_get_pin_positions` or the library symbol) and **the footprint's
  pads** (`lib_get_footprint_info`): number, name and electrical type. The pads' places and
  sizes against the datasheet's land pattern are `lib_check_footprint`'s (`land_pattern` from
  the datasheet; it names each pad off by more than 0.05 mm).
- **Exposed pads and mounting tabs.** An exposed pad the symbol does not list passes ERC, yet
  it is usually both the part's heat path and an electrical connection. The datasheet's pin
  table or notes say what it joins (ground, a supply, or "may be left floating").

A mismatch is clear to the person when it names the part, the pin, what the symbol says and
what the datasheet says, with the page.

## Values the distributors do not give

Distributor specs (`lib_get_component_specs`) often lack what a design needs: thermal
resistance (θJA, θJC), absolute maximum ratings, dropout at the load current, a derating
curve. The datasheet has them, with a page that lets the person check the value; a value from
memory or from a similar part has no such source.

## A part with no KiCad symbol

`lib_generate_symbol_from_pintable` builds a symbol from an extracted pin table; the footprint
assigned to it matches the package drawing. A generated symbol can be checked like any other.
