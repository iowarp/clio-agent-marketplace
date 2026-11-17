---
name: resolve-region
title: Resolve a Region
description: Ground a place name or explicit coordinates into one fixed analysis region (bounding box, or center and radius) plus the names a catalog might file it under, before any station, dataset or coverage claim, with provenance and stated assumptions.
keywords:
- level:L1
- geospatial
- region
---

# Resolve a region

Use this before searching, filtering or clipping data by place, unless the
current region in the conversation already matches the request. It produces
two things: the **region** every later step uses, and the **place names** a
catalog search can use.

## The region

- **Coordinates given:** keep them verbatim; do not geocode.
- **A place name:** when `geo_geocode` is available, call it once with the
  full name (with state or country when known); if the result is empty or
  ambiguous, try once more with a more specific name. Without it, take the
  location from a cited source you look up (an official gazetteer, the
  managing agency's page, a watershed or boundary service) and record that
  source. A failed lookup is a blocker to report or a question for the user,
  never a gap to fill from memory.
- **Shape:** a lake, basin, forest or county is an area: prefer its bounding
  box (or its boundary polygon when a boundary layer is at hand) over a point
  and radius. A town or a station is a point: use a radius.
- **Size:** use the user's radius or extent exactly. Without one, choose one
  conservative extent for the kind of question, label it as an assumption, and
  keep it fixed for every later filter in the same analysis.

## The names to search by

Catalog records rarely carry coordinates you can search, and they name places
inconsistently. List, from the geocoder result or the cited source:

- the place's own name and its common short form;
- the larger units that contain it: county or counties, state, national forest
  or park, watershed or basin (HUC name when known);
- the main features inside it (the lake, the river, the range);
- the agencies that manage it, when they publish data under their own name.

These are search terms, not claims that data exists. Datasets that cover the
region without naming it (national and statewide layers) are found by theme,
not by name; see the source's discovery skill.

## Record

Record the resolved label, the bounds as `[west, south, east, north]` in
degrees (or center and radius), the geocoder's result or cited source, the
name list, and any assumption. Make no claim about stations or data in this
step. A small map of the region helps only when the place could be confused;
load `present-interactive-analysis` for it.
