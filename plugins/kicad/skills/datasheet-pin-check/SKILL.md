---
name: datasheet-pin-check
description: Before layout, check every IC's symbol and footprint pin map against its datasheet's pin table, take missing values from the datasheet with the page cited, and build a missing symbol from the pin table.
---

# Datasheet pin check

A wrong pin map is the error no later check catches: ERC and DRC pass on a board whose
regulator's input and output are swapped. Run this before layout, for every IC, connector
and polarized part.

## For each part

1. **Get the datasheet.** `lib_get_datasheet_url` (or the BOM's datasheet link). Save the PDF
   in the project folder and read it with `view_pdf`, so every value you take from it comes
   with the page you read it on.
2. **Read the pin table** for the exact package (the same part in another package has
   another pin map).
3. **Compare** with the symbol's pins (`sch_get_pin_positions` or the library symbol) and the
   footprint's pads (`lib_get_footprint_info`): every number, name and electrical type. The
   pads' places and sizes against the datasheet's land pattern are `lib_check_footprint`'s
   (`land_pattern` from the datasheet; it names each pad off by more than 0.05 mm).
   Exposed pads and mounting tabs count. An exposed pad the symbol does not list is a
   mismatch even when ERC passes: it is usually both the part's heat path and an electrical
   connection, and the datasheet's pin table or notes say what it joins (ground, a supply, or
   "may be left floating"). Connect it as the datasheet says, with the page.
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
