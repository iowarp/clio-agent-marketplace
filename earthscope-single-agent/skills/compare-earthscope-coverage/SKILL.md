---
name: compare-earthscope-coverage
title: Compare EarthScope Station Coverage
description: Compare tool-observed GNSS station counts across several fixed regions without staging station time-series resources.
---

Use this skill for metadata-only regional comparisons. For every named region,
load `resolve-earthscope-region`, resolve it fresh when requested, and preserve
the same user-specified radius for every region. Reuse one already-staged cleaned
station catalog when its provenance is current; do not download or stage any
station time-series CSV.

Call `geo_filter_points_by_radius` separately for each grounded center with the
same catalog and explicit `Latitude`, `(deg)`, and `Site` columns. Report the exact
`within_radius_count` values, filter status, input rows, and invalid skips. Rank
regions only from those returned counts. If any filter is structurally invalid,
show that region as unavailable rather than comparing a fabricated zero.

An A2UI table and map are useful here: each table row and map point must come from
the geocoder/filter results, and the visible label must make the shared radius and
metadata-only scope clear.
