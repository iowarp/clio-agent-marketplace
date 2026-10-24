---
name: count-stations-in-region
title: Count Stations in a Region
description: In a child agent, resolve one assigned region and count the stations of an already normalized catalog within the assigned radius, returning the counts and their evidence.
effect: spawn_subagent_with_skill
keywords:
- level:L1
- geodesy
- stations
---

You are already running this skill in the delegated child. Do not delegate
again; complete the assignment directly.

The assignment must give the full place name, the radius, the normalized
catalog's path and its id, latitude and longitude column names. If any is
missing, return that as the blocker instead of inferring it from another
region. Do not stage any time series and do not create views; the parent
owns the comparison.

1. Resolve the place with `geo_geocode`; retry once with a more specific name
   only when the first result is empty or ambiguous.
2. Call `geo_filter_points_by_radius` with the assigned radius, catalog path
   and columns.
3. Return the resolved label and center, the radius, `within_radius_count`,
   the input rows, the invalid skips, the filter status and the tool
   evidence. If a tool fails structurally, return the failure, not a zero.
