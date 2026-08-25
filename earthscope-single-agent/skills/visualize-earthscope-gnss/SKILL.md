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
completeness, continuity, or quality. Preserve the artifact identity created at
the tool boundary in `workflow_state.visualization` and `workflow_state.artifact`.
