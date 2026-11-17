---
name: harmonize-layers
title: Harmonize and Merge Layers
description: Use when layers from different sources or organizations must be compared or joined - stations against rasters, polygons against rasters, rasters against rasters, layers with different CRSs, units or time bases. Puts them on one footing with stated methods, reports what overlaps, and records the merge with each layer's provenance.
keywords:
- level:L1
- geospatial
- harmonization
---

# Harmonize and merge layers

A correlation across sources is only as good as the step that puts the layers
on one footing. Do it explicitly, with the method named, and write down what
could not be matched.

## 1. Inventory

Make one table, a row per layer: source and organization, what it measures,
geometry (points, lines, polygons, raster cells and their size, point spacing),
CRS and vertical datum, units and where they came from, the time it describes
(a date, a period, a vintage or "undated"), the region it covers, and its
completeness (paging, decimation, depth). Fill it from each fetch's record,
not from memory. A blank cell is a caveat to carry forward.

## 2. Common footing

- **CRS:** do the analysis in one projected CRS for the region (the local UTM
  zone, or an equal-area CRS for areas across zones). Use `geoprocess_reproject`;
  areas come from `overlay_features`, which works in an equal-area CRS.
- **Vertical datum:** elevations from different sources (ellipsoid heights,
  NAVD88, local datums) differ by metres. Compare datums before differencing;
  `raster_difference` lists a mismatch or an undeclared datum as a caveat.
  Convert only with a documented transform, and say which one.
- **Units:** convert to one unit per quantity, writing down the factor and its
  source. A layer whose units cannot be established is described, not
  combined.
- **Time base:** state what each layer's time means (an acquisition date, a
  fire year, a survey season, a model vintage). Pair layers by an explicit rule
  (same year, the closest survey before an event, a seasonal window) and list
  the pairs. A layer whose time cannot be determined stays in the analysis as
  "undated", flagged.

## 3. Co-registration

Pick the method from the geometry pair and name it in the result:

| Pair | Method |
| --- | --- |
| Points (stations, plots) and a raster | `zonal_statistics` with point features: nearest cell, or a buffer mean (`buffer_m`) sized to the point's footprint or position uncertainty |
| Polygons and a raster | `zonal_statistics` over the polygons: per-zone statistics plus the share of each zone with data |
| Polygons and polygons | `overlay_features` (intersection, identity), after `dissolve` where a layer's polygons overlap |
| Raster and raster | resample the finer onto the coarser grid, or difference on one grid with `raster_difference`; say which resampling method was used and why (nearest for classes, average or bilinear for continuous values) |

## 4. Coverage report

Every merge says, for the analysis region:

- **overlaps:** layers that have data in the region, with the area or share
  covered;
- **does not overlap:** layers whose data stops short of it, with where it ends;
- **could not be determined:** layers with no usable extent or time, and why.

Never fill a gap from a layer that does not cover it, and never let an empty
region read as zero.

## 5. Record the merge

Write the hypothesis or question before the merge result, then cite each
layer's evidence. When the science log is available (`science-log`), record
the merge there: the question, the inventory table, the footing decisions, the
co-registration methods, the coverage report, and the result with its
uncertainty. Next to each derived file, write a provenance record listing its
inputs (source, layer, URL or catalog identity, the time fetched), the
operations applied in order with their parameters, and the caveats. The
analysis can then be rerun or audited from the files alone.
