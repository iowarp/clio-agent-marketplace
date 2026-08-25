---
name: acquire-earthscope-gnss
title: Acquire EarthScope GNSS Data
description: Discover, normalize, spatially rank, and stage a real EarthScope GNSS station series from a grounded region without inventing paths or stations.
---

Use this skill only after the region is grounded. Perform the following procedure
yourself in causal order.

1. Find the EarthScope station catalog with
   `ndp_search_datasets(search_terms=["earthscope", "converted"], limit=10)`.
   Select the returned `earthscope_converted_data.csv` resource URL.
2. Stage that catalog by URL with `ndp_stage_resource`. When an active workspace
   root is available, use it as `output_dir`. Copy the returned raw path.
3. Normalize the catalog with `pandas_filter_data`, keeping rows where `Latitude`
   is between -90 and 90 and writing `earthscope_stations_clean.csv` under the
   active workspace root. This also rewrites the source as UTF-8. The verified
   columns are station id `Site`, latitude `Latitude`, and longitude `(deg)`;
   `Longitude` is elevation and must never be used as longitude.
4. Call `geo_filter_points_by_radius` once with the fixed region center/radius and
   explicit columns `Latitude`, `(deg)`, and `Site`. Preserve the returned ranked
   points, `total_points`, `within_radius_count`, and `skipped_invalid`.

A zero-candidate conclusion is valid only when the filter structurally succeeded,
input rows were nonzero, invalid skips were not substantial, and
`within_radius_count` is zero. Otherwise record `filter_failed`; retry once with
the same radius and explicit columns. Never widen the region to manufacture a
candidate.

For a request that needs a station series, walk the ranked station ids in order:

- search with `ndp_search_datasets(dataset_title=<station id>, limit=20)`;
- choose a returned per-station CSV resource whose filename starts with that exact
  station id;
- stage its URL with `ndp_stage_resource(max_bytes=60000000)`;
- copy the returned station id, URL, path, and size byte-for-byte.

Try the next ranked station only when the current station has no matching CSV or
staging fails. A successful acquisition requires an on-disk station time-series
CSV and `analysis_ready=true`; the metadata catalog alone is `metadata_only`.
Never derive a station id or filename from a city name.
