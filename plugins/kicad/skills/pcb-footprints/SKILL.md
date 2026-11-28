---
name: pcb-footprints
description: "Check a KiCad footprint against a datasheet's or supplier's land pattern (pad by pad, recorded), and give every part on a board a footprint and a 3D body that match its datasheet: find one in KiCad's libraries, or generate it with KiCad Library Tools, check it against the land pattern and the KiCad Library Conventions, and assign it."
---

# Footprints and bodies from datasheets

The datasheet is the source: every pad, body dimension and pin number comes from a page of the
part's datasheet (`view_pdf` gives the page). `datasheet-pin-check` covers the pins; this skill
is about the land pattern and the body.

## The ladder, for each symbol on the schematic

1. **A footprint in KiCad's libraries.** `lib_search_footprints` searches by the package name
   and the datasheet's package code. `lib_check_footprint` with `land_pattern` taken from the
   datasheet's recommended land pattern (pad number, centre x/y and size in mm, in the
   footprint's frame: origin at the package centre, y down) says whether one matches.
2. **A generator family.** `lib_list_footprint_families` lists KiCad Library Tools' families;
   with `family` it shows a real entry to copy the format from. Families cover packages and
   connector series alike (`query="connector"`: a JST, Molex or Hirose SMD series is an entry
   in `connector/SMD_single_row_plus_mounting_pad`, a THT series has its own family). An entry
   written from the datasheet's package drawing and land pattern, with the page in
   `size_source`, goes to `lib_generate_footprint` (footprint and STEP body into the project
   library), and `lib_check_footprint` checks it against the land pattern.
3. **No family fits** (an odd module, or a part whose shape no family's entry can describe,
   seen in the family list): a KicadModTree script for that part and a CadQuery body go to
   `lib_generate_footprint_custom`.
4. **Assign**: `lib_assign_footprint`, and `lib_set_3d_model_path` when the body is not the
   footprint's own.

`lib_check_footprint` fails on a KLC error or a pad off the datasheet by more than the
tolerance (0.05 mm), and names each. KLC warnings are listed for your judgement; KLC naming
rules are notes in a project library.

## The person sees what you made

A generated footprint renders with `kicad-cli fp export svg` (then to PNG); beside a crop of
the datasheet's land pattern page, shown in the conversation (registered as artifacts, or on
one surface), it is something the person can judge. A path in your text is not: the person can
only accept what they have seen. The record in
`libs/footprint-records.json` keeps where each footprint came from, its datasheet pages and its
last check.

## Bodies for every part

A board's STEP used for a case or a fit needs a body for every footprint.
`lib_get_footprint_3d_model`, or the warnings of `export_step`, list the footprints whose model
is missing or does not resolve. A footprint from a family has the Library Tools model; any
other takes an **envelope** body built with CadQuery from the datasheet's maximum dimensions,
with a pin-1 mark, saved as STEP in `libs/3d` and assigned with `lib_set_3d_model_path` (a path
under `${KIPRJMOD}`), recorded as `envelope` in the footprint's record. When no footprint's
model resolves, KiCad's 3D library is likely not installed; `pcb-enclosure` (step 1) has the
choices.
