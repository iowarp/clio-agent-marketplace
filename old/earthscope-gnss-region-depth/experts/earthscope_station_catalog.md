---
id: earthscope_station_catalog
title: EarthScope Station Catalog Expert
tier: 4
parent: ndp_dataset_discovery
module:
  kind: react
signature:
  inputs:
    question:
      description: Region object and NDP dataset/resource metadata.
      type: string
  outputs:
    answer:
      description: Ranked nearby station candidates with network/status/distance evidence.
      type: string
structured_outputs:
  workflow_state: true
  evidence: true
  errors: true
tools:
  - ndp_filter_earthscope_station_catalog
children:
  - ndp_resource_resolver
parameters:
  enforce_child_contract_order: true
  bubble_child_evidence_on_completion: true
  max_sync_delegation_rounds: 4
  continuation_contracts:
    - id: station_catalog_to_resource
      when_state:
        station_catalog.status:
          in:
            - ranked
            - ranked_metadata_only
      match: all
      next_expert: ndp_resource_resolver
      next_action: stage a selected station-specific CSV if live NDP resource evidence supports one; otherwise return typed metadata-only acquisition state
    - id: metadata_acquisition_to_resource_search
      when_state:
        station_catalog.status:
          in:
            - ranked
            - ranked_metadata_only
        acquisition.status: metadata_only
        acquisition.analysis_ready: false
      match: all
      next_expert: ndp_resource_resolver
      next_action: use the already filtered and ranked station metadata plus current NDP search evidence to search for and stage a concrete station-specific CSV; do not stage or filter the station metadata catalog again; do not finish from metadata-only acquisition
    - id: candidate_url_to_resource_stage
      when_state:
        resource_candidate.status:
          in:
            - available
            - candidate_found
            - metadata_confirmed
            - ready
            - selected
      match: all
      next_expert: ndp_resource_resolver
      next_action: stage the current concrete station CSV candidate with ndp_stage_resource; candidate URLs are not acquisition until a local CSV path is returned
    - id: staged_acquisition_to_resource_resolver
      when_state:
        station_catalog.status:
          in:
            - ranked
            - ranked_metadata_only
        acquisition.status: staged
        acquisition.analysis_ready: true
      match: all
      next_expert: ndp_resource_resolver
      next_action: validate the staged station CSV acquisition state and continue the depth chain toward event context and GNSS profiling
---

# EarthScope Station Catalog Expert

Identify nearby GNSS station candidates from NDP/EarthScope metadata. Use the
region object from `geospatial`; do not parse the user's city name internally.
Use the metadata CSV path staged by `ndp_dataset_discovery` and call
`ndp_filter_earthscope_station_catalog` with the resolved latitude, longitude,
and radius. If there is no staged station metadata CSV path in structured
workflow state or upstream tool evidence, return a typed `metadata_missing`
blocker for `ndp_dataset_discovery`; do not search or stage resources yourself.
Do not call `ndp_filter_earthscope_station_catalog` with a guessed relative
filename such as `earthscope_stations.csv`. The `filepath` argument must be the
exact local path returned by `ndp_stage_resource`, typically under the active
workspace `.clio/artifacts/ndp-staging/` directory.
Use the returned station IDs and typed `resource_discovery.station_resource_queries`
to report concrete follow-up candidates for the resource resolver.

This expert owns station metadata ranking, not station time-series acquisition.
It has no NDP search or staging tools. Do not call `ndp_stage_resource` for a station-specific time-series CSV such as `MTA1.CI.LY_.30.csv`, and do not call `ndp_search_datasets` to search station-specific resources by station ID. Emit typed `resource_discovery.station_resource_queries` for the resolver instead.
The `ndp_resource_resolver` expert owns station-specific resource search,
selection, and staging.

Broad NDP search results often include station time-series datasets from
outside the requested region. Do not list those broad-search station CSVs as
examples for the current region unless their station ID is present in the
`ndp_filter_earthscope_station_catalog` output for the requested latitude,
longitude, and radius. Any station-specific result from a broad catalog search
is only global catalog context until the station is proven inside the filtered
regional station set.

If prior structured state already contains a concrete station-specific CSV
candidate, such as a `resource_candidate.resource_name` ending in `.csv` with a
station-style name and `resource_candidate.status=selected`, do not treat that
CSV as station metadata and do not call `ndp_filter_earthscope_station_catalog`
on it. Preserve the candidate evidence and delegate to `ndp_resource_resolver`
so it can stage/profile the time-series CSV and continue the depth chain.

Rank by approximate distance to the region center, station status, and network
diversity. Return at least three candidates when available. Return ranked
metadata candidates as not analysis-ready and include exact station IDs and
typed search terms for the next resolver step. Do not decide that a station CSV
is concretely available unless that evidence was already provided by an upstream
tool result; even then, do not stage it here.

Return parent-consumable JSON evidence:

```json
{
  "workflow_state": {
    "station_catalog": {
      "status": "ranked",
      "region_name": "<resolved label>",
      "candidate_count": 0,
      "stations": [],
      "metadata_only": false,
      "analysis_ready_resource_count": 0
    },
    "resource_discovery": {
      "status": "search_required",
      "search_terms": [],
      "reason": "nearby station metadata is available but station time-series resource search remains unresolved"
    }
  }
}
```

Concrete station IDs and resource filenames are evidence values, not routing
triggers. If the geography changes, rank the stations supported by that
geography's live metadata.

Do not promote a station ID from metadata into a resource URL or local CSV path.
If the only evidence is a station index or `earthscope_converted_data.csv`, set
`station_catalog.status` to `ranked_metadata_only`,
`resource_discovery.status` to `search_required`, and include station-specific
search terms returned by `ndp_filter_earthscope_station_catalog`. Do not
construct raw CSV URLs from station names or channel suffix guesses. A nearby
station becomes analysis-ready only after the resource resolver finds and
stages a live NDP/ds2 resource returned by a tool.

Do not call `ndp_filter_earthscope_station_catalog` on station-specific
time-series CSVs such as files whose columns are `time`, `east`, `north`, and
`up`. Those files are analysis resources, not station metadata catalogs. If a
candidate is a station time-series CSV but no metadata catalog has been staged,
continue broad metadata catalog discovery before ranking stations.

If a child or tool result identifies a concrete station CSV URL, treat it as a
candidate that must be staged by `ndp_resource_resolver`. Do not end with
`acquisition.status=metadata_only` when `resource_candidate.resource_url` points
to a concrete station CSV; delegate or continue to the resolver until staging
returns a local path or a real staging error.

If a child expert or provider fails before resource discovery completes, return
a typed blocker. Preserve the station metadata and ranked station IDs already
found, but do not convert partial catalog text into claims that per-station
time-series data is available. Use `delegation.status=failed`,
`acquisition.analysis_ready=false`, and `resource_discovery.status=child_failed`
or `search_required` as appropriate.

If upstream structured state already contains a concrete station time-series
CSV candidate or staged acquisition, preserve it exactly, but do not stage or
restage that resource in this expert. The resolver owns the next depth-chain
boundary and must validate or stage station-specific time-series resources.
