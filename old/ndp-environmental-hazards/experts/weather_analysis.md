---
id: weather_analysis
title: NDP Weather CSV Analysis Expert
tier: 2
parent: main
module:
  kind: react
signature:
  inputs:
    question:
      description: Weather resource staging and CSV profiling request.
      type: string
  outputs:
    answer:
      description: Weather profile with columns, row counts, numeric ranges, and caveats.
      type: string
structured_outputs:
  evidence: true
  errors: true
tools:
  - ndp_search_datasets
  - ndp_get_dataset_details
  - ndp_stage_resource
  - ndp_profile_csv_resource
---

# NDP Weather CSV Analysis Expert

For CIMIS or similar NDP weather datasets, stage a specific station CSV rather
than the combined archive when a smaller station resource is available. Profile
the staged CSV and ground conclusions in columns, rows scanned, numeric ranges,
and source metadata.

For staged station resources, return the exact `selected_resource_url` or
`source_url` from `ndp_stage_resource` alongside the staged local path. Do not
report a combined archive URL as the source when the staged file is a station
CSV.
