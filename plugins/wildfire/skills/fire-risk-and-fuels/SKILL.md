---
name: fire-risk-and-fuels
title: Fire Risk, Hazard and Fuels Layers
description: Use for questions about wildfire risk, hazard, burn probability, exposure or fuels (fuel models, fuel load, canopy cover, height and base height, ladder fuels) in a region or within zones such as watersheds, parcels or communities. Covers reading what each index means, units and vintage, comparing layers, and summarising them honestly.
keywords:
- level:L1
- wildfire
---

# Fire risk, hazard and fuels layers

Risk products look alike on a map and mean different things. Read what each
layer is before combining it.

## Know the layer

For each candidate, record from its record, metadata or documentation:

- **What it estimates:** burn probability (chance a cell burns in a year),
  fire intensity or flame length (how severe if it burns), hazard (likelihood
  and intensity together), exposure or risk to something valued (homes,
  watersheds, habitat), or a fuel property (fuel model class, fuel load,
  canopy cover, height or base height, bulk density).
- **Units and scale:** a probability (0 to 1), a class code with a legend, a
  physical quantity (tons per acre, metres, percent), or a relative index with
  no physical unit. Many raster services do not embed units; take them from
  the record and say so.
- **Vintage:** the year the fuels or the model represent. Fuels change after
  fire and treatment; a pre-fire fuels layer over a recent burn is out of
  date there.
- **Resolution and method:** cell size, and whether it was modelled or
  observed.

Class codes (fuel models, risk classes) are categories: resample them with
nearest, report shares per class, and never average them.

## Fetch and summarise

- Fetch a region with `read_raster_window` (WCS coverages through
  `coverage_id`). Check `valid_fraction`: a state or regional product can stop
  at a boundary inside your region.
- **Over zones** (watersheds, parcels, communities, habitat polygons):
  `zonal_statistics` with the zones and `by` the zone name. Report the mean
  and the high tail (a high percentile or the share above a stated threshold),
  not only the mean, and each zone's coverage share.
- **Within or outside fire perimeters:** clip or mask by dissolved perimeters
  (see `fire-perimeters`) to compare burned and unburned fuels, keeping in
  mind the fuels vintage relative to the fire date.

## Compare honestly

Two products' "high risk" are not the same quantity. Compare rankings or
shares within each layer, not raw values across layers, unless they estimate
the same quantity in the same units. When indices disagree, report the
disagreement and what each measures. Do not average them into a new index.
