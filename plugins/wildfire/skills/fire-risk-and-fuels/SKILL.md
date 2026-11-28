---
name: fire-risk-and-fuels
title: Fire Risk, Hazard and Fuels Layers
description: Use for questions about wildfire risk, hazard, burn probability, exposure or fuels (fuel models, fuel load, canopy cover, height and base height, ladder fuels) in a region or within zones such as watersheds, parcels or communities. Covers reading what each index means, units and vintage, comparing layers, and summarising them honestly.
keywords:
- level:L1
- wildfire
---

# Fire risk, hazard and fuels layers

Risk products look alike on a map and mean different things, so a combination
depends on what each layer is.

## What a layer is

Each candidate's record, metadata or documentation gives:

- **What it estimates:** burn probability (chance a cell burns in a year),
  fire intensity or flame length (how severe if it burns), hazard (likelihood
  and intensity together), exposure or risk to something valued (homes,
  watersheds, habitat), or a fuel property (fuel model class, fuel load,
  canopy cover, height or base height, bulk density).
- **Units and scale:** a probability (0 to 1), a class code with a legend, a
  physical quantity (tons per acre, metres, percent), or a relative index with
  no physical unit. Many raster services do not embed units; the record supplies
  them.
- **Vintage:** the year the fuels or the model represent. Fuels change after
  fire and treatment; a pre-fire fuels layer over a recent burn is out of
  date there.
- **Resolution and method:** cell size, and whether it was modelled or
  observed.

Class codes (fuel models, risk classes) are categories: nearest-neighbour
resampling and shares per class keep them meaningful, and an average of codes
means nothing.

## Fetching and summarising

- `read_raster_window` fetches a region (WCS coverages through
  `coverage_id`). `valid_fraction` shows coverage: a state or regional product
  can stop at a boundary inside the region.
- **Over zones** (watersheds, parcels, communities, habitat polygons):
  `zonal_statistics` with the zones and `by` the zone name. The mean alone hides
  the high tail (a high percentile or the share above a stated threshold), and
  each zone's coverage share qualifies its numbers.
- **Within or outside fire perimeters:** a clip or mask by dissolved perimeters
  (see `fire-perimeters`) compares burned and unburned fuels, which depends on
  the fuels vintage relative to the fire date.

## Comparing layers

Two products' "high risk" are not the same quantity. Rankings or shares within
each layer compare; raw values across layers compare only when they estimate the
same quantity in the same units. Disagreeing indices are a finding, explained by
what each measures; an average of them is a new, undefined index.
