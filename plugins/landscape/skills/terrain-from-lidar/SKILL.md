---
name: terrain-from-lidar
title: Terrain and Hydrology from Lidar
description: Use for terrain or hydrology questions answered from lidar or DEMs - bare-earth and surface models, canopy or vegetation height, slope and aspect, flow direction and accumulation, stream networks and contributing area, and elevation or snow-depth change by differencing two surveys or a snow-on and snow-off pair.
keywords:
- level:L1
- terrain
- hydrology
- lidar
---

# Terrain and hydrology from lidar

## Surfaces

- **Bare earth (DTM, "be"):** ground only (lidar class 2). It is the basis for
  slope, hydrology and snow depth.
- **Surface (DSM, highest hit, "hh"):** tops of trees and buildings.
- **Canopy height:** surface minus bare earth on one grid
  (`raster_difference`). It is not tree height where returns did not reach the
  ground.
- **From points:** `read_point_cloud` with `classifications=[2]` for ground.
  `spacing` bounds the usable cell size (a cell a few times the point
  spacing). The terrain server grids points (`pointcloud_read`, which writes a
  DEM) when no DEM product exists.

`read_raster_window` reads just the region; native resolution matters when
slopes or channels do. A decimated DEM smooths slopes and shortens streams, which
qualifies any result from one.

## Terrain

`dem_terrain` gives slope, aspect and suitability on a DEM; the cell size and
the CRS qualify them. Slope needs metres in all three axes, so a geographic DEM
needs reprojecting first.

## Hydrology

`scripts/flow_routing.py` (numpy only) fills depressions, computes D8 flow
direction and accumulation, and extracts streams above a contributing-area
threshold:

```bash
python scripts/flow_routing.py DEM.tif --out-prefix OUT --stream-area-km2 0.5
```

It writes `OUT_accumulation.tif`, `OUT_streams.tif` and a JSON summary (cell
size, filled cells, outlet cells, stream cells, the largest contributing
area). Lakes and flat areas route arbitrarily after filling, which qualifies
streams in a region that has them. The stream threshold is a choice that fits
the question and defines the network; a mapped stream layer, when one exists,
checks the extracted streams.

## Change by differencing

Elevation change, erosion and snow depth are differences of two surfaces:
`raster_difference` with the later (or snow-on) surface first.

- Both surfaces need the **same vertical datum and units**. The tool flags a
  mismatch or an undeclared datum, and a difference across one is not a change.
- **Snow depth** is snow-on minus snow-off bare earth. Vegetation and steep
  slopes add error, which a summary by land cover or slope class shows.
  Negative depths are error, not negative snow: their share measures it, and
  clipping them silently hides it. Snow water equivalent needs a density, from
  measurements or a stated assumption.
- The overlap of the two surveys, the dates of each, and the net volume with
  its sign describe the change.
