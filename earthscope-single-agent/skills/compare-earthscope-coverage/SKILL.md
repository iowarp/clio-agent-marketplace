---
name: compare-earthscope-coverage
title: Compare EarthScope Station Coverage
description: Compare tool-observed GNSS station counts across several fixed regions without staging station time-series resources.
---

Use this skill for metadata-only regional comparisons. For every named region,
resolve it fresh when requested and preserve the same user-specified radius for
every region. Reuse one already-staged cleaned station catalog when its
provenance is current; do not download or stage any station time-series CSV.

Before dispatching any region, the parent must have the literal path to one
current cleaned station catalog and the verified `Latitude`, `(deg)`, and `Site`
columns. If retained state does not contain that path, use the normal EarthScope
catalog discovery, staging, and cleaning tools in the parent first. Catalog
metadata preparation is allowed for this comparison; station time-series
staging is not. Do not dispatch an assignment with a missing or described-only
catalog path.

For three or more independent regions, the parent is one participant in the
parallel work: keep exactly one region in the parent and fan out only the other
regions by calling `load_skill(skill_id="delegate-earthscope-region",
task=<specific assignment>)` once per delegated region before doing the retained
region directly. Never delegate all regions, even when the user says to resolve
all regions in parallel. Each task must contain the full place, common radius,
the literal cleaned catalog path, and the explicit `Latitude`, `(deg)`, and
`Site` columns. Collect the returned task ids with `wait_agent_tasks` under a
bounded timeout. For one or two regions, or when parallelism adds no value,
perform them directly.

Call `geo_filter_points_by_radius` separately for each grounded center with the
same catalog and explicit columns. Report the exact `within_radius_count` values,
filter status, input rows, and invalid skips. Rank regions only from those
returned counts. If any filter is structurally invalid, show that region as
unavailable rather than comparing a fabricated zero.

Comparing two or more resolved regions benefits from direct spatial and tabular
interaction. After all regions return, load `present-interactive-analysis` and
create or update `earthscope-coverage` with a compact count table and map. Every
row and point must come from the geocoder/filter results, and the visible label
must make the shared radius and metadata-only scope clear.
