---
name: visualize-earthscope-gnss
title: Visualize EarthScope GNSS Data
description: Produce a real, provenance-tracked GNSS plot from the exact staged CSV and confirmed columns.
---

Use this skill only when the user requests a plot or when a plot materially helps
answer the current question. Confirm the exact time and displacement column names
from the profile, then call `plot_plot_timeseries` on the staged station CSV.

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

The PNG is a durable export, not the primary interactive plot. When the user asks
to plot a data series, a live chart materially helps: load
`present-interactive-analysis` and create or update `earthscope-timeseries` using
`clio.time-series.v1`, the registered staged CSV artifact URI, the confirmed time
column as `xKey`, and confirmed displacement columns as `yKeys`. Also retain the
PNG artifact for download and provenance, exposed as a secondary action rather
than a second inline image. Use image-only presentation only when a data-backed
chart is unavailable, and state that presentation limitation explicitly.
