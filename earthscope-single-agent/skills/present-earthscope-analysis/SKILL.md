---
name: present-earthscope-analysis
title: Present EarthScope Analysis
description: Turn already observed EarthScope results into one compact, interactive A2UI surface with useful tables, maps, metrics, plots, and artifacts.
---

Use the root-only `create_a2ui_surface` tool after the scientific evidence needed
for the current answer exists. Reuse the stable surface id
`earthscope-analysis`. A2UI is presentation, not a second analysis path.

Prefer one `Tabs` root when several views are useful. Good tabs are:

- Summary: `clio.status.v1`, `clio.metric.v1`, and a concise limitation callout;
- Stations: `clio.data-table.v1` with tool-observed ids, distances, coordinates,
  or region counts;
- Map: `clio.map.v1` with geocoded/filter-observed points;
- Series: `clio.time-series.v1` only when the tool supplied bounded real rows;
- Artifact: `clio.artifact.v1` for a registered CSV, PNG, or report.

Use the official flat component array with exactly one top-level component whose
id is `root`. Tabs reference separately declared child ids. Tables have no `title`
property; compose a Text label when needed. Keep data bounded and readable. Never
paste JSON into a Text component, invent series rows, or use a surface to hide a
tool failure. Call the tool once per coherent revision and require
`rendered=true` and `state=ready` before describing the surface as available.
