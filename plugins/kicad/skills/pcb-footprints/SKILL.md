---
name: pcb-footprints
description: "Check a KiCad footprint against a datasheet's or supplier's land pattern (pad by pad, recorded), and give every part on a board a footprint and a 3D body that match its datasheet: find one in KiCad's libraries, or generate it with KiCad Library Tools, check it against the land pattern and the KiCad Library Conventions, and assign it."
---

# Footprints and bodies from datasheets

The datasheet is the source: every pad, body dimension and pin number comes from a page of the
part's datasheet (read it with `view_pdf`, and cite the page). Run `datasheet-pin-check` for
the pins; this skill is about the land pattern and the body.

## The ladder, for each symbol on the schematic

1. **A footprint in KiCad's libraries.** Search by the package name and the datasheet's package
   code (`lib_search_footprints`). Accept one only after `lib_check_footprint` passes with
   `land_pattern` taken from the datasheet's recommended land pattern (pad number, centre x/y
   and size in mm, in the footprint's frame: origin at the package centre, y down).
2. **A generator family.** `lib_list_footprint_families` lists KiCad Library Tools' families;
   with `family` it shows a real entry to copy the format from. Families cover packages and
   connector series alike (`query="connector"`: a JST, Molex or Hirose SMD series is an entry
   in `connector/SMD_single_row_plus_mounting_pad`, a THT series has its own family). Write the
   entry from the datasheet's package drawing and land pattern, with the page in
   `size_source`, then `lib_generate_footprint` (footprint and STEP body into the project
   library), then `lib_check_footprint` against the land pattern.
3. **No family fits** (an odd module, or a part whose shape no family's entry can describe,
   seen in the family list): write a KicadModTree script for that part and a CadQuery body,
   `lib_generate_footprint_custom`, then `lib_check_footprint`.
4. **Assign**: `lib_assign_footprint`, and `lib_set_3d_model_path` when the body is not the
   footprint's own.

`lib_check_footprint` fails on a KLC error or a pad off the datasheet by more than the
tolerance (0.05 mm), and names each. KLC warnings are listed for your judgement; KLC naming
rules are notes in a project library. Fix the entry or script and generate again.

## The person sees what you made

Render a generated footprint (`kicad-cli fp export svg`, then to PNG) beside a crop of the
datasheet's land pattern page and show both in the conversation, side by side (registered as
artifacts, or on one surface), and look at them yourself first. A path in your text is not
showing them: the person can only accept what they have seen. A **custom** footprint is
assigned only after the person accepts it; a generated one is assigned and shown, and the
person can reject it. The record in
`libs/footprint-records.json` keeps where each footprint came from, its datasheet pages and its
last check.

## Bodies for every part

Before a board's STEP is used for a case or a fit, every footprint needs a body. List the
footprints whose model is missing or does not resolve (`lib_get_footprint_3d_model`, or the
warnings of `export_step`). For each: the Library Tools model when the footprint came from a
family; otherwise an **envelope** body built with CadQuery from the datasheet's maximum
dimensions, with a pin-1 mark, saved as STEP in `libs/3d` and assigned with
`lib_set_3d_model_path` (a path under `${KIPRJMOD}`). Record it as `envelope` in the footprint's
record. When no footprint's model resolves, KiCad's 3D library is likely not installed: say so,
and see `pcb-enclosure` (step 1) for the choices.
