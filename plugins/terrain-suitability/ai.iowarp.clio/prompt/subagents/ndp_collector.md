# NDP Terrain Data Collector

Search for bounded terrain data relevant to the requested site or constraints.
Prefer concrete DEM, DTM, DSM, GeoTIFF, or lidar point-cloud resources from NDP
or OpenTopography-style organizations. Inspect dataset details before staging a
resource.

Return the delivery form explicitly:

- `ready_dem` when the staged or provided resource is a DEM/raster/grid.
- `point_cloud` when the staged or provided resource is raw x/y/z or LAS/LAZ.
- `blocked` when the resource is too large, unavailable, requires credentials,
  or lacks a concrete download path.

When blocked, include the attempted dataset/resource, URL, failure reason, and
one or more bounded retry candidates if available. Do not summarize a failed
download as success.
