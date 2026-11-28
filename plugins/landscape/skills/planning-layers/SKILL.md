---
name: planning-layers
title: Planning Layers for a Basin or Region
description: Use for land-use and conservation planning questions over a region - how much of it is habitat of a kind, sensitive land, stream environment or floodplain, how those relate to a lake, river, roads or development, which parcels or zones intersect them - from agency planning layers such as habitat, land capability, soils, stream zones and regulatory boundaries.
keywords:
- level:L1
- planning
- habitat
---

# Planning layers

Regional planning agencies publish many thematic layers for one area: wildlife
and fish habitat, land capability or soil classes, stream and floodplain zones,
impervious cover, parcels, plan boundaries. Each answers a narrow question; a
good answer combines them without double counting.

## Finding and reading the layers

- An agency's catalog entries often each point to one layer of a map service.
  The service layer (`fetch_features`) serves the same features when a file
  download fails.
- Each layer's fields and what its classes mean come from the layer's
  metadata or the agency's documentation. A class code without a legend is a
  caveat, not a guess.
- Each layer has a date or vintage. Habitat and land-cover maps are snapshots.

## "How much"

- **Covered area of one theme:** the theme's polygons dissolved
  (`overlay_features` with `dissolve`) give its hectares. Several habitat
  layers (for example one per species) overlap: each theme's area and the
  dissolved area of the union are meaningful; their sum is not a total.
- **Share of the region:** a clip to the region's boundary polygon
  (`clip_features`), with the same boundary as the denominator. Whether open
  water is in or out of the denominator changes the share.
- **By class:** a dissolve `by` the class field gives per-class hectares.

## "How does it relate to the lake, river or roads"

- **Distance bands:** bands around the feature (for example 0 to 100 m,
  100 to 500 m, beyond) as polygons, intersected with the theme
  (`overlay_features` with `intersection`), give the area per band. Buffers
  are a short script in a projected CRS, and the band edges define the result.
- **Adjacency:** the count of theme polygons that touch or lie within a stated
  distance of the feature.
- **Overlap of two themes** (habitat in a stream zone, habitat on steep
  land-capability classes): their intersection gives the shared area and each
  theme's share of it.

## Caveats to carry

Different layers come from different surveys and dates, and their boundaries
do not line up exactly. Slivers from boundary mismatch are not real overlap;
a stated minimum area separates them from real intersections. Regulatory
boundaries define where rules apply, not the ecological extent of a habitat.
