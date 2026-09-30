---
name: visualize-earthscope-gnss
title: Visualize EarthScope GNSS Data
description: Present a real, interactive GNSS time series from the exact staged CSV and confirmed columns, with a static export only when requested.
---

Use this skill only when the user requests a plot or when a plot materially helps
answer the current question. Confirm the exact time and displacement column names
from the profile. The primary plot is a live, data-backed A2UI chart, not a PNG.

First load `present-interactive-analysis`, which covers writing a custom
Vega-Lite spec with Altair for a chart no named preset fits. Reuse the
registered staged CSV artifact from `workflow_state` when it already exists;
do not register the same CSV again. Then create or update `earthscope-timeseries`
using exactly one primary `clio.chart.v1`, the registered staged CSV artifact
URI as `dataUri`, and a `spec` built on `alt.NamedData("source")` that
`transform_fold`s the confirmed displacement columns (`east`, `north`, and
`up` when all are present) into one `component`/`displacement` pair and draws
one line per component: the confirmed time column on `x`, `displacement` on
`y`, `component` on `color`. No preset reshapes a wide table this way, so
author the spec directly with `present-interactive-analysis`'s script and let
its guard check pass before calling `create_a2ui_surface`. Require
`rendered=true` and `state=ready` before moving on or saying the plot is
available. Call these tools one at a time in causal order; do not batch a
skill load, artifact registration, or surface creation into one model response.

For the normal request to "plot" or "show" the series, stop after the interactive
chart is ready and answer from the observed chart/data state. The renderer owns
hover values, legend interaction, zoom, and pan over its bounded CSV preview.

Generate a static PNG only when the user explicitly asks for an image, download,
export, report asset, or durable static figure, or when the interactive chart is
unavailable and you clearly report that degraded presentation. In that case call
`plot_plot_timeseries` on the staged station CSV after the live chart is ready.

Use the exact `acquisition.local_path` as `data_path`. Plot confirmed `east`,
`north`, and `up` columns by default when all are present. Provide an explicit
absolute PNG `output_path` under the active workspace root, named from the staged
station id rather than the city. For a user-requested comparison, use only exact
additional staged paths as overlays.

Report only what the plot tool returned: output path, size, plotted columns, and
plotted row scope. A rendered line is not proof of full-file cadence,
completeness, continuity, duration, or quality. `data_points` is the number the
plot accepted, not proof that it consumed every file row or covered the full
catalog interval. Say "full file" or "complete window" only when an independent
uncapped observation established the total and the plotted scope matches it.
Preserve the artifact identity created at
the tool boundary in `workflow_state.visualization` and `workflow_state.artifact`.

The PNG is a durable export, never the primary interactive plot. Do not add
`clio.artifact.v1`, `Image`, an image tab, or a second surface for the PNG when
the interactive chart is present. If a PNG was explicitly requested, register it
so the conversation can expose it as a compact attachment and the workspace
canvas can open it on demand; registration is sufficient. Never place the static
image below, beside, or inside the interactive chart.
