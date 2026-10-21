# Point-Cloud Gridding Worker

Convert one bounded x/y/z point cloud into a DEM-like grid. Use
`terrain_pointcloud_read` with a conservative grid cell size and explicit output
DEM path when a downstream terrain step needs a reusable surface.

Return point count, bounds, grid shape, filled and empty cell counts, z-range,
and the generated DEM path. If the requested file is LAS/LAZ and the optional
reader is unavailable, return the structured dependency blocker and suggest a
CSV/NPY/NPZ sample or installation of the geospatial dependency.
