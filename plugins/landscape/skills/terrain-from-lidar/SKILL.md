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

## Pick the surface

- **Bare earth (DTM, "be"):** ground only (lidar class 2). It is the basis for
  slope, hydrology and snow depth.
- **Surface (DSM, highest hit, "hh"):** tops of trees and buildings.
- **Canopy height:** surface minus bare earth on one grid
  (`raster_difference`). It is not tree height where returns did not reach the
  ground.
- **From points:** `read_point_cloud` with `classifications=[2]` for ground.
  Check `spacing` against the cell size you need (a cell a few times the point
  spacing). Grid the points with the terrain server (`pointcloud_read`, which
  writes a DEM) when no DEM product exists.

Read only the region (`read_raster_window`), at native resolution when slopes
or channels matter. A decimated DEM smooths slopes and shortens streams; say so
when you use one.

## Terrain

`dem_terrain` gives slope, aspect and suitability on a DEM. Report the cell
size and the CRS. Slope needs metres in all three axes, so reproject
geographic DEMs first.

## Hydrology

`scripts/flow_routing.py` (numpy only) fills depressions, computes D8 flow
direction and accumulation, and extracts streams above a contributing-area
threshold:

```bash
python scripts/flow_routing.py DEM.tif --out-prefix OUT --stream-area-km2 0.5
```

It writes `OUT_accumulation.tif`, `OUT_streams.tif` and a JSON summary (cell
size, filled cells, outlet cells, stream cells, the largest contributing
area). Lakes and flat areas route arbitrarily after filling; state that when
the region has them. Choose the stream threshold for the question and report
it. Compare the extracted streams with a mapped stream layer when one exists.

## Change by differencing

Elevation change, erosion and snow depth are differences of two surfaces:
`raster_difference` with the later (or snow-on) surface first.

- Both surfaces need the **same vertical datum and units**. The tool flags a
  mismatch or an undeclared datum; resolve it before reporting a number.
- **Snow depth** is snow-on minus snow-off bare earth. Vegetation and steep
  slopes add error; summarise by land cover or slope class when it matters.
  Negative depths are error, not negative snow: report their share rather than
  clipping them silently. Snow water equivalent needs a density, from
  measurements or a stated assumption.
- Report the overlap of the two surveys, the dates of each, and the net volume
  with its sign.
