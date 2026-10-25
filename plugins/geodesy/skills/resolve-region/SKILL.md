---
name: resolve-region
title: Resolve a Region
description: Ground a place name or explicit coordinates into one fixed analysis region (center and radius, or bounds) before any station or dataset claim, with provenance and stated assumptions.
keywords:
- level:L1
- geodesy
- geospatial
---

# Resolve a region

Use this before filtering stations or data by place, unless the current
region in the conversation already matches the request.

- **Coordinates given:** keep them verbatim; do not geocode.
- **A place name:** call `geo_geocode` once with the full name (with state or
  country when known). If the result is empty or ambiguous, try once more with
  a more specific name. A failed lookup is a blocker to report, never a gap to
  fill from memory.
- **Radius:** use the user's radius exactly. Without one, choose one
  conservative radius for the kind of question (a city, a fault segment, a
  region), label it as an assumption, and keep it fixed for every later
  filter in the same analysis.

Record the resolved label, center, radius or bounds, the geocoder's result,
and any assumption. Make no claim about stations or data in this step. A
small map of the center helps only when the place could be confused; load
`present-interactive-analysis` for it.
