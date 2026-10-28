---
name: compare-station-coverage
title: Compare Station Coverage
description: Compare how many stations of one discovered catalog fall within the same radius of several regions, from metadata only, optionally counting independent regions in child agents.
keywords:
- level:L1
- geodesy
- stations
- comparison
---

# Compare station coverage

A coverage comparison counts catalog stations near each region. It uses
station metadata only: do not stage any station's time series for it.

1. **One catalog, normalized.** Find and stage the station catalog with the
   source skill's discovery procedure, then normalize it with
   `station-catalogs`. Every region is counted against the same normalized
   copy, by its literal path. The raw staged catalog is never that copy.
2. **One radius.** Resolve each region with `resolve-region` and use the same
   user-given (or once-assumed) radius for all of them.
3. **Count.** Call `geo_filter_points_by_radius` per region with the
   normalized path and the explicit `latitude`, `longitude` and `id` columns.
   Keep `within_radius_count`, the input rows and the invalid skips. A region
   whose filter failed structurally is shown as unavailable, never as zero.
4. **Fan out only when it pays.** For three or more independent regions you
   may count each in a child with `count-stations-in-region`, passing the
   full place name, the radius, the normalized catalog path and the column
   names in the task; a child cannot discover or normalize the catalog. Wait
   for every child, check its counts against its evidence, and compare in the
   parent. Concurrent children are admission-bounded, so more of them do not
   necessarily finish sooner. For one or two regions, count directly.
5. **Present** a compact table (region, center, radius, count, input rows,
   skipped) and, when it helps, a map of the centers and counted stations
   (`present-interactive-analysis`), labelled with the shared radius and the
   metadata-only scope. Rank regions only from the returned counts.
