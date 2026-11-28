---
name: resolve-region
title: Resolve a Region
description: Grounds a place name or explicit coordinates into one fixed analysis region (bounding box, or center and radius) plus the names a catalog might file it under, ahead of any station, dataset or coverage claim, with provenance and stated assumptions.
keywords:
- level:L1
- geospatial
- region
---

# Resolve a region

Searching, filtering or clipping data by place depends on a fixed region, unless
the current region in the conversation already matches the request. Resolving
one produces two things: the **region** every later step uses, and the **place
names** a catalog search can use.

## The region

- **Coordinates given:** they are the region verbatim; geocoding them would
  only move them.
- **A place name:** `geo_geocode`, when available, takes the full name (with
  state or country when known); an empty or ambiguous result often resolves with
  a more specific name. Without it, a cited source (an official gazetteer, the
  managing agency's page, a watershed or boundary service) gives the location,
  and that source is part of the record. A failed lookup is a blocker or a
  question for the person; a location from memory is unverified.
- **Shape:** a lake, basin, forest or county is an area, which a bounding box
  (or its boundary polygon when a boundary layer is at hand) describes better
  than a point and radius. A town or a station is a point with a radius.
- **Size:** the person's radius or extent is exact. Without one, a conservative
  extent for the kind of question is an assumption, labelled as such, and it
  stays fixed for every later filter in the same analysis so results stay
  comparable.

## The names to search by

Catalog records rarely carry coordinates that can be searched, and they name
places inconsistently. The geocoder result or the cited source gives:

- the place's own name and its common short form;
- the larger units that contain it: county or counties, state, national forest
  or park, watershed or basin (HUC name when known);
- the main features inside it (the lake, the river, the range);
- the agencies that manage it, when they publish data under their own name.

These are search terms, not claims that data exists. Datasets that cover the
region without naming it (national and statewide layers) are found by theme,
not by name; the source's discovery skill covers that.

## The record

The resolved label, the bounds as `[west, south, east, north]` in degrees (or
center and radius), the geocoder's result or cited source, the name list, and
any assumption. Resolving a region says nothing yet about stations or data. A
small map of the region helps only when the place could be confused;
`present-interactive-analysis` draws one.