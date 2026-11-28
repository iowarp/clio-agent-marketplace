---
name: count-stations-in-region
title: Count Stations in a Region
description: In a child agent, resolves one assigned region and counts the stations of an already normalized catalog within the assigned radius, returning the counts and their evidence.
effect: spawn_subagent_with_skill
keywords:
- level:L1
- geodesy
- stations
---

This skill runs inside the delegated child a coverage comparison spawned; the
parent owns the comparison, any further fan-out, staging and views.

The assignment gives the full place name, the radius, the normalized catalog's
path and its id, latitude and longitude column names. A missing item is a
blocker to return; inferring it from another region would count against the
wrong inputs.

- `resolve-region` (with `geo_geocode` when it is available) resolves the place;
  a more specific name helps when the first result is empty or ambiguous.
- `geo_filter_points_by_radius` when it is available, else
  `station_catalog.py within` from the `station-catalogs` skill, counts with the
  assigned radius, catalog path and columns.
- The parent needs the resolved label and center, the radius,
  `within_radius_count`, the input rows, the invalid skips, the filter status
  and the tool evidence. A structural tool failure is a failure, not a zero.