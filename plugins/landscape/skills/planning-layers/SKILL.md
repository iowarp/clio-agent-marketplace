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

## Find and read the layers

- An agency's catalog entries often each point to one layer of a map service.
  Get the features from the service layer (`fetch_features`) when a file
  download fails; it serves the same features.
- Read each layer's fields and what its classes mean (from the layer's
  metadata or the agency's documentation). A class code without a legend is a
  caveat, not a guess.
- Note each layer's date or vintage. Habitat and land-cover maps are snapshots.

## Answer "how much"

- **Covered area of one theme:** dissolve the theme's polygons
  (`overlay_features` with `dissolve`) before reporting hectares. Several
  habitat layers (for example one per species) overlap: report each theme's
  area and the dissolved area of the union, never the sum as a total.
- **Share of the region:** clip to the region's boundary polygon
  (`clip_features`), and use the same boundary for the denominator. Say
  whether open water is in or out of the denominator.
- **By class:** dissolve `by` the class field and report the per-class
  hectares.

## Answer "how does it relate to the lake, river or roads"

- **Distance bands:** build bands around the feature (for example 0 to 100 m,
  100 to 500 m, beyond) as polygons, intersect the theme with them
  (`overlay_features` with `intersection`), and report the area per band.
  Write the buffers with a short script in a projected CRS. State the band
  edges.
- **Adjacency:** count theme polygons that touch or lie within a stated
  distance of the feature.
- **Overlap of two themes** (habitat in a stream zone, habitat on steep
  land-capability classes): intersect them and report the shared area and
  each theme's share of it.

## Caveats to carry

Different layers come from different surveys and dates, and their boundaries
do not line up exactly. Slivers from boundary mismatch are not real overlap:
drop intersections below a stated minimum area and say so. Regulatory
boundaries define where rules apply, not the ecological extent of a habitat.
