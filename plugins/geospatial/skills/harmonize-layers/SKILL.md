---
name: harmonize-layers
title: Harmonize and Merge Layers
description: Use when layers from different sources or organizations must be compared or joined - stations against rasters, polygons against rasters, rasters against rasters, layers with different CRSs, units or time bases. Covers putting them on one footing with stated methods, what overlaps, and recording the merge with each layer's provenance.
keywords:
- level:L1
- geospatial
- harmonization
---

# Harmonize and merge layers

A correlation across sources is only as good as the step that puts the layers
on one footing. That step is reproducible when its methods are named, and
honest when what could not be matched is written down.

## Inventory

A table with a row per layer: source and organization, what it measures,
geometry (points, lines, polygons, raster cells and their size, point spacing),
CRS and vertical datum, units and where they came from, the time it describes
(a date, a period, a vintage or "undated"), the region it covers, and its
completeness (paging, decimation, depth). Each fetch's record fills it; memory
does not. A blank cell is a caveat that carries forward.

## Common footing

- **CRS:** one projected CRS for the region (the local UTM zone, or an
  equal-area CRS for areas across zones). `geoprocess_reproject` converts;
  areas come from `overlay_features`, which works in an equal-area CRS.
- **Vertical datum:** elevations from different sources (ellipsoid heights,
  NAVD88, local datums) differ by metres, so differencing across datums is
  wrong; `raster_difference` lists a mismatch or an undeclared datum as a caveat.
  A conversion is valid only with a documented transform, named in the result.
- **Units:** one unit per quantity, with each conversion factor and its source.
  A layer whose units cannot be established can be described, not combined.
- **Time base:** each layer's time means something specific (an acquisition
  date, a fire year, a survey season, a model vintage). Layers pair by an
  explicit rule (same year, the closest survey before an event, a seasonal
  window), and the list of pairs shows it. A layer whose time cannot be
  determined stays in the analysis as "undated", flagged.

## Co-registration

The method follows from the geometry pair, and the result names it:

| Pair | Method |
| --- | --- |
| Points (stations, plots) and a raster | `zonal_statistics` with point features: nearest cell, or a buffer mean (`buffer_m`) sized to the point's footprint or position uncertainty |
| Polygons and a raster | `zonal_statistics` over the polygons: per-zone statistics plus the share of each zone with data |
| Polygons and polygons | `overlay_features` (intersection, identity), after `dissolve` where a layer's polygons overlap |
| Raster and raster | resample the finer onto the coarser grid, or difference on one grid with `raster_difference`; the resampling method and its reason (nearest for classes, average or bilinear for continuous values) are part of the result |

## Coverage report

A merge's coverage, for the analysis region:

- **overlaps:** layers that have data in the region, with the area or share
  covered;
- **does not overlap:** layers whose data stops short of it, with where it ends;
- **could not be determined:** layers with no usable extent or time, and why.

A layer that does not cover a gap cannot fill it, and an empty region is not
zero.

## The merge record

The hypothesis or question comes before the merge result, with each layer's
evidence. When the science log is available (`science-log`), the merge fits
there: the question, the inventory table, the footing decisions, the
co-registration methods, the coverage report, and the result with its
uncertainty. A provenance record next to each derived file lists its inputs
(source, layer, URL or catalog identity, the time fetched), the operations
applied in order with their parameters, and the caveats. The analysis can then
be rerun or audited from the files alone.