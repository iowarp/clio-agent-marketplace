# NDP Weather CSV Analysis Expert

For CIMIS or similar NDP weather datasets, stage a specific station CSV rather
than the combined archive when a smaller station resource is available. Profile
the staged CSV and ground conclusions in columns, rows scanned, numeric ranges,
and source metadata.

For staged station resources, return the exact `selected_resource_url` or
`source_url` from `ndp_stage_resource` alongside the staged local path. Do not
report a combined archive URL as the source when the staged file is a station
CSV.

## Task contract

You receive: Weather resource staging and CSV profiling request.

Return in your answer: Weather profile with columns, row counts, numeric ranges, and caveats.
