---
name: ts-diagram
title: T-S Diagram
description: Draw a T-S diagram (Conservative Temperature against Absolute Salinity) with labelled density contours and the samples coloured by water mass, from a TEOS-10 profile table, with clio.chart.v1 and the spec and script shipped with this skill.
keywords:
- level:L1
- ocean
- chart
- water-masses
---

# T-S diagram

1. Start from a profile table with `SA` and `CT` (from `teos10`) and, when
   water masses are assigned, `water_mass` (from `water_masses`).
2. Add the density contours to the same table with the bundled script,
   run with `shell_bash`:
   `uv run <this skill>/scripts/isopycnals.py <table> <output> [--interval <kg/m3>]`.
   It keeps every cast row (`kind = "cast"`) and appends isopycnal rows
   (`kind = "isopycnal"`, `sigma0`, `label`) across the data's range at a
   round interval.
3. Register the output and draw `clio.chart.v1` with the Vega-Lite spec in
   `ts-diagram.vl.json` beside this file, unchanged, as `spec`, and the
   output as `dataUri`.
4. Link it to the section or map by cast: a shared `/selection/<key>` with
   `selectionField` `profile`.

Without `water_mass`, add a `calculate` step that sets it to the cast or a
depth band, and say which.
