---
name: get-geospatial-data
title: Get Geospatial Data from Services
description: Use when a dataset is served rather than downloadable as one file - an ArcGIS REST layer, OGC WFS or WCS, STAC, a folder of raster tiles with a VRT, a remote GeoTIFF/COG, or a lidar point cloud (Entwine/EPT, COPC) - or when a file link fails. Check the source covers the region from the data itself, then fetch only the region, and report how complete the result is.
keywords:
- level:L1
- geospatial
- data-access
---

# Get geospatial data from services

Most Earth-science data is served, not posted as one file. Fetch the part
inside the analysis region (from `resolve-region`) instead of downloading
whole collections, and keep a record of what was fetched and how complete it
is.

## 1. Know what the link is

Call `geoservices_describe_geo_service` on the link before fetching. It says
what the URL speaks and returns the layers, feature types, coverages, raster
header or point-cloud extent. A web page or viewer link often wraps a service:

| Link looks like | What to fetch |
| --- | --- |
| `…/rest/services/…/FeatureServer` or `MapServer` (often labelled "Esri REST" or "ArcGIS GeoServices") | a layer: `…/MapServer/<layer id>` with `fetch_features` |
| A hub "download" link (GeoJSON, CSV, KML, shapefile zip) that fails | the record's Esri REST layer, which serves the same features |
| `…/ows`, `…/wfs`, `…/wcs`, or `service=WFS/WCS` | WFS feature type with `fetch_features`; WCS coverage with `read_raster_window` and `coverage_id` |
| `.tif`, `.vrt`, `.img`, `.adf` (ArcGrid) | `read_raster_window`; give the `.vrt` for a tiled dataset when there is one |
| An Entwine/Potree viewer link, `ept.json`, `.copc.laz` | `read_point_cloud` |
| STAC catalog, collection or `/search` | `search_stac`, then read the assets it returns |

A WMS or map-tile link draws pictures, not data. Look for the WCS, WFS or REST
layer of the same product. A record's format label can be blank or wrong, so
judge from the URL and from what describe returns.

## 2. Check coverage from the data

A declared extent can be missing, world-wide or malformed. `describe` reports
`coverage` as `overlaps`, `disjoint` or `undetermined`, preferring the extent it
measured from the data. When it is undetermined, ask the data:
`fetch_features` with `count_only` for a vector layer; a small
`read_raster_window` for a raster, where `valid_fraction` 0 means the region
holds no data even though the bounds overlap. Report "does not cover" or
"could not be determined" as findings, with the reason.

## 3. Fetch only the region

- **Features:** `fetch_features` with the region `bbox`, a `where` clause when
  the question selects records (a year, a class), and `max_features` sized to
  the question. If `paging.complete` is false, say the result is truncated or
  narrow the request.
- **Rasters:** `read_raster_window` with the region and a `max_cells` budget.
  It reports `decimation`. Use native resolution (a larger budget or a smaller
  region) when the science depends on fine detail, such as slopes or narrow
  channels. Several tiles, including tiles in different UTM zones, are
  mosaicked in one call. `region_not_covered` names the part of the region no
  source reaches (its fraction and box): that part is nodata in the output, so
  add the tiles that cover it, or report the gap and leave it out of every
  statistic.
- **Point clouds:** `read_point_cloud` with the region, `max_points`, and
  `classifications=[2]` for ground. `complete: false` means a coarser level of
  detail was read. The `spacing` tells you whether it is fine enough.
- **Units:** many raster services do not embed units (`units: null`). Take them
  from the catalog record or the layer's documentation, and say where they came
  from.

## 4. Record what you have

For each fetched layer, record: the source URL and layer or coverage, the
region, the time the data describes (from the record or the layer), the CRS,
the resolution or point spacing, completeness (paging, decimation, depth), the
units and where they came from, and the output path. A downstream step or merge
cites this record. Analysis on the fetched files uses the `geoprocess` tools:
`reproject`, `clip_features`, `overlay_features`, `zonal_statistics`,
`raster_difference`.

When a service fails (HTTP error, timeout, refused query), report the typed
reason the tool returned and try the record's other service link before
concluding the data is unavailable. Do not reconstruct data from a picture or a
viewer.
