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
station metadata only; no station's time series is needed for it.

- **One catalog, normalized.** The station catalog comes from the source
  skill's discovery procedure and is normalized with `station-catalogs`. The
  counts are comparable when every region is counted against the same
  normalized copy, by its literal path; the raw staged catalog is not that copy.
- **One radius.** `resolve-region` fixes each region, and one radius (given by
  the person, or assumed once) holds for all of them.
- **Counting.** Per region, the normalized path is filtered with the explicit
  `latitude`, `longitude` and `id` columns: `geo_filter_points_by_radius`
  when it is available, else `station_catalog.py within`. Counts are
  comparable only from one method. `within_radius_count`, the input rows and
  the invalid skips are the evidence. A region whose filter failed structurally
  is unavailable, not zero.
- **Fan-out.** For three or more independent regions, each can be counted in a
  child with `count-stations-in-region`; the task carries the full place name,
  the radius, the normalized catalog path and the column names, since a child
  cannot discover or normalize the catalog. The comparison happens in the parent
  once every child has returned and its counts match its evidence. Concurrent
  children are admission-bounded, so more of them do not necessarily finish
  sooner, and one or two regions are quicker to count directly.
- **Presentation.** A compact table (region, center, radius, count, input rows,
  skipped) and, when it helps, a map of the centers and counted stations
  (`present-interactive-analysis`), labelled with the shared radius and the
  metadata-only scope. A ranking of regions holds only as far as the returned
  counts.