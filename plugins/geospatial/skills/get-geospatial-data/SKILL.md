---
name: get-geospatial-data
title: Get Geospatial Data from Services
description: Use when a dataset is served rather than downloadable as one file - an ArcGIS REST layer, OGC WFS or WCS, STAC, a folder of raster tiles with a VRT, a remote GeoTIFF/COG, or a lidar point cloud (Entwine/EPT, COPC) - or when a file link fails. Covers checking from the data itself that the source covers the region, fetching only the region, and how complete the result is.
keywords:
- level:L1
- geospatial
- data-access
---

# Get geospatial data from services

Most Earth-science data is served, not posted as one file. The part inside the
analysis region (from `resolve-region`) is usually all that is needed, and whole
collections are large. A record of what was fetched and how complete it is lets
later steps cite it.

## What the link is

`geoservices_describe_geo_service` says what a URL speaks and returns the layers,
feature types, coverages, raster header or point-cloud extent, without fetching
data. A web page or viewer link often wraps a service:

| Link looks like | What to fetch |
| --- | --- |
| `…/rest/services/…/FeatureServer` or `MapServer` (often labelled "Esri REST" or "ArcGIS GeoServices") | a layer: `…/MapServer/<layer id>` with `fetch_features` |
| A hub "download" link (GeoJSON, CSV, KML, shapefile zip) that fails | the record's Esri REST layer, which serves the same features |
| `…/ows`, `…/wfs`, `…/wcs`, or `service=WFS/WCS` | WFS feature type with `fetch_features`; WCS coverage with `read_raster_window` and `coverage_id` |
| `.tif`, `.vrt`, `.img`, `.adf` (ArcGrid) | `read_raster_window`; the `.vrt` of a tiled dataset reads all its tiles |
| An Entwine/Potree viewer link, `ept.json`, `.copc.laz` | `read_point_cloud` |
| STAC catalog, collection or `/search` | `search_stac`, then the assets it returns |

A WMS or map-tile link draws pictures, not data; the same product usually has a
WCS, WFS or REST layer. A record's format label can be blank or wrong; the URL
and what describe returns are more reliable.

## Coverage, from the data

A declared extent can be missing, world-wide or malformed. `describe` reports
`coverage` as `overlaps`, `disjoint` or `undetermined`, preferring the extent it
measured from the data. When it is undetermined, the data answers:
`fetch_features` with `count_only` for a vector layer; a small
`read_raster_window` for a raster, where `valid_fraction` 0 means the region
holds no data even though the bounds overlap. "Does not cover" and "could not be
determined" are findings, each with its reason.

## Fetching the region

- **Features:** `fetch_features` takes the region `bbox`, a `where` clause when
  the question selects records (a year, a class), and `max_features`. When
  `paging.complete` is false, the result is truncated; a narrower request
  completes it.
- **Rasters:** `read_raster_window` takes the region and a `max_cells` budget,
  and reports `decimation`. Science that depends on fine detail, such as slopes
  or narrow channels, needs native resolution (a larger budget or a smaller
  region). Several tiles, including tiles in different UTM zones, are mosaicked
  in one call. `region_not_covered` names the part of the region no source
  reaches (its fraction and box): that part is nodata in the output, so either
  more tiles cover it or it is a gap that no statistic can include.
- **Point clouds:** `read_point_cloud` takes the region, `max_points`, and
  `classifications=[2]` for ground. `complete: false` means a coarser level of
  detail was read. The `spacing` says whether it is fine enough.
- **Units:** many raster services do not embed units (`units: null`). The
  catalog record or the layer's documentation gives them, and where they came
  from is part of the result.

## The fetch record

A useful record of each fetched layer holds the source URL and layer or
coverage, the region, the time the data describes (from the record or the
layer), the CRS, the resolution or point spacing, completeness (paging,
decimation, depth), the units and where they came from, and the output path. A
downstream step or merge cites it. Analysis on the fetched files uses the
`geoprocess` tools: `reproject`, `clip_features`, `overlay_features`,
`zonal_statistics`, `raster_difference`.

When a service fails (HTTP error, timeout, refused query), the tool returns a
typed reason, and the record's other service link may still work; one failed
link does not mean the data is unavailable. A picture or a viewer is not data.