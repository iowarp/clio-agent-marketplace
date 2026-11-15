---
name: datasheet-pin-check
description: Before layout, check every IC's symbol and footprint pin map against its datasheet's pin table, take missing values from the datasheet with the page cited, and build a missing symbol from the pin table.
---

# Datasheet pin check

A wrong pin map is the error no later check catches: ERC and DRC pass on a board whose
regulator's input and output are swapped. Run this before layout, for every IC, connector
and polarized part.

## For each part

1. **Get the datasheet.** `lib_get_datasheet_url` (or the BOM's datasheet link); ingest the
   PDF where the session keeps documents, so you can cite pages.
2. **Read the pin table** for the exact package (the same part in another package has
   another pin map).
3. **Compare** with the symbol's pins (`sch_get_pin_positions` or the library symbol) and the
   footprint's pads (`lib_get_footprint_info`): every number, name and electrical type.
   Exposed pads and mounting tabs count.
4. **Stop on a mismatch.** Report the part, the pin, what the symbol says and what the
   datasheet says, with the page. Do not lay out a part whose pins disagree.

## Values the distributors do not give

Distributor specs (`lib_get_component_specs`) often lack what the design needs: thermal
resistance (θJA, θJC), absolute maximum ratings, dropout at the load current, a derating
curve. Take the value from the ingested datasheet and record the page it came from with the
value. Never fill one in from memory or from a similar part.

## A part with no KiCad symbol

Build the symbol from the pin table you extracted with `lib_generate_symbol_from_pintable`,
assign a footprint that matches the package drawing, then run this check on the new symbol
like any other.
