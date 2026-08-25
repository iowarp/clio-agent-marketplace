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

Use exact catalog props rather than inferring them:

- `clio.callout.v1` requires `title`, `body`, and `severity`; it does not accept
  `text` or `level`;
- `clio.artifact.v1` requires `name`, `uri`, and `mediaType`. Use the registered
  artifact URI, or `artifact://<artifact-id>` when registration returns only an
  id. It does not accept `artifact_id`, `kind`, `path`, or a bare filesystem
  path;
- `Image` uses `url`, not `src`, and only `https:`, `artifact:`, or `resource:`
  URLs are accepted. Prefer `clio.artifact.v1` for generated workspace files.
- `clio.metric.v1` represents one metric with `label` and `value`. Several
  values require several metric components referenced by a `Row` or `Grid`; it
  does not accept a `metrics` aggregate.

Use this known-good structure as the baseline and replace only the observed
values and bounded rows. Do not add properties that are not shown here:

```yaml
- id: root
  component: Tabs
  tabs:
    - {title: Summary, child: summary}
    - {title: Stations, child: stations}
    - {title: Map, child: map}
    - {title: Artifact, child: artifact}
- id: summary
  component: Column
  children: [status, metrics, limitation]
- id: status
  component: clio.status.v1
  label: Analysis
  state: completed
  detail: Concise observed scope
- id: metrics
  component: Row
  children: [metric-count, metric-selected]
- id: metric-count
  component: clio.metric.v1
  label: Candidates
  value: 0
- id: metric-selected
  component: clio.metric.v1
  label: Selected station
  value: Unavailable
- id: limitation
  component: clio.callout.v1
  title: Limitation
  body: Concise observed limitation
  severity: warning
- id: stations
  component: clio.data-table.v1
  columns: [{key: id, label: Station}, {key: distance_km, label: Distance (km)}]
  rows: []
- id: map
  component: clio.map.v1
  points: [{id: center, label: Observed center, latitude: 0, longitude: 0}]
- id: artifact
  component: clio.artifact.v1
  name: result.png
  uri: artifact://registered-artifact-id
  mediaType: image/png
```

The example coordinates and values are placeholders, not evidence. Replace
them with current tool-observed facts; omit a tab when no corresponding evidence
exists.

Use the official flat component array with exactly one top-level component whose
id is `root`. Tabs reference separately declared child ids. Tables have no `title`
property; compose a Text label when needed. Keep data bounded and readable. Never
paste JSON into a Text component, invent series rows, or use a surface to hide a
tool failure. Call the tool once per coherent revision and require
`rendered=true` and `state=ready` before describing the surface as available.
