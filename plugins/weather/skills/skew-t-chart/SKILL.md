---
name: skew-t-chart
title: Skew-T Chart
description: Draw atmospheric soundings as a skew-T log-p chart (temperature, dewpoint and the surface parcel against pressure) from the soundings profile table, with clio.chart.v1 and the spec template shipped with this skill.
keywords:
- level:L1
- weather
- sounding
- chart
---

# Skew-T chart

The skew-T is an ordinary `clio.chart.v1` with the Vega-Lite spec in
`skew-t.vl.json` beside this file, passed unchanged as the chart's `spec`, with
the soundings profile table as `dataUri` (the table `soundings` writes, one row
per level with `profile`, `pressure`, `temperature_c`, `dewpoint_c` and
`parcel_temperature_c`).

- Pressure runs down a log axis from the surface; temperature is skewed
  with height, so a sounding leaning right is warm aloft, as on a printed
  skew-T. The axis title says the temperature is skewed; the tooltip shows
  the real value.
- One chart per sounding reads best: `dataQuery.filter` on `profile` selects one
  sounding. Several soundings in one chart are drawn as separate lines.
- The sounding's indices (CAPE, CIN, lifted index, LCL) come from the indices
  table and read best next to the chart, not in it.
- A profile table that names its columns differently (another source) needs a
  `calculate` step that maps them, and the mapping is part of the chart's
  provenance.