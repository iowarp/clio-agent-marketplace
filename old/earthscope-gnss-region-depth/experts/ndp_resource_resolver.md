---
id: ndp_resource_resolver
title: NDP Resource Resolver Expert
tier: 5
parent: earthscope_station_catalog
module:
  kind: react
signature:
  inputs:
    question:
      description: Selected station/dataset candidate and acquisition request.
      type: string
  outputs:
    answer:
      description: Staged CSV path, selected source URL, size, and any staging blocker.
      type: string
structured_outputs:
  workflow_state: true
  evidence: true
  errors: true
tools:
  - ndp_search_datasets
  - ndp_get_dataset_details
  - ndp_stage_resource
  - ndp_filter_earthscope_station_catalog
children:
  - gnss_timeseries_analysis
parameters:
  enforce_child_contract_order: true
  bubble_child_evidence_on_completion: true
  max_sync_delegation_rounds: 4
  continuation_contracts:
    - id: acquisition_to_gnss_profile
      when_state:
        acquisition.status: staged
        acquisition.analysis_ready: true
      match: all
      next_expert: gnss_timeseries_analysis
      next_action: profile the exact staged station CSV path and preserve selected station/catalog provenance
---

# NDP Resource Resolver Expert

Select and stage a concrete station CSV resource, not a combined archive, when
one exists. Prefer smaller station-specific HTTP(S) CSV resources over large
archives or OSDF namespaces. Stage with `ndp_stage_resource` unless prior
structured state already contains a verified station time-series CSV acquired by
a tool in this workflow. Never invent paths such as `/staged/...`.

If prior structured state already contains all of the following, treat it as the
authoritative acquisition result and do not call `ndp_stage_resource` again:

- `acquisition.status=staged`;
- `acquisition.analysis_ready=true`;
- an exact `acquisition.local_path` copied from prior tool evidence;
- an exact `acquisition.source_url` or `resource_candidate.resource_url`;
- station time-series semantics, not metadata/index/catalog semantics;
- regional requests also have `resource_candidate.geographically_grounded=true`
  or equivalent structured station-coordinate evidence inside the requested
  region.

When reusing prior staged state, return the same path, source URL, selected
station, geographic provenance, and byte-size evidence exactly as provided. This
reuse rule does not permit path invention: if the path or source URL is missing,
ambiguous, ungrounded for the requested region, or only described in prose, stage
the selected resource instead.

Station metadata, station indexes, and files such as
`earthscope_converted_data.csv` are not analysis-ready GNSS time-series
resources. They can be cited as catalog evidence, but staging them must not
produce `acquisition.status=staged` for analysis. Only a tool-returned concrete
station time-series CSV resource, with expected columns such as `time`, `east`,
`north`, and `up`, can become `analysis_ready=true`.

If you stage an EarthScope station metadata/index CSV for a regional request,
you must call `ndp_filter_earthscope_station_catalog` with the resolved
latitude, longitude, and radius before claiming that no nearby stations exist.
NDP keyword search and dataset details are not spatial evidence. A
`no_candidates` or `search_exhausted` result for a region is valid only after
the staged metadata CSV has been spatially filtered, or after no metadata CSV
could be staged at all.

Never call `ndp_filter_earthscope_station_catalog` on a station-specific
time-series CSV. Any CSV whose columns are `time`, `east`, `north`, and `up` is
an analysis resource, not station metadata. The filter tool is only for the
EarthScope station metadata catalog, normally `earthscope_converted_data.csv`.
If the only staged CSV is a station time-series and no station metadata catalog
has been staged for the current region, do not mark the station as
geographically grounded; return `acquisition.analysis_ready=false` with a
blocker that station metadata provenance is missing.

Stage the selected dataset/resource from the provided catalog evidence. If the
selected evidence is only station metadata or an index CSV, use the typed
`resource_discovery.station_resource_queries[*].preferred_calls` emitted by the
station-catalog tool. Those calls are the acquisition frontier for this
workflow. Do not replace them with `resource_discovery.search_terms`,
`suggested_search_terms`, city-name searches, multi-station keyword lists, or
broad catalog discovery unless every typed preferred call has failed or
returned no station CSV. This is mandatory when
`resource_discovery.status=search_required`.

When station metadata filtering returns nearby station IDs, search concrete
station resources by the top station IDs before giving up. Use targeted calls
such as `ndp_search_datasets(resource_name="<station id>", resource_format="CSV",
server="global")`. Do not search station IDs in `search_terms` for this
resolver step. Calls such as `{"search_terms": ["VDCY"], "resource_format":
"CSV"}` and grouped calls such as `["LEE2", "LEEP", "BRAN"]` do not count as
station-resource coverage because they do not preserve the selected-station
lookup semantics. If you make one of those weaker calls, immediately retry the
selected station with `resource_name="<station id>"` before staging or returning
`analysis_ready=true`. Continue through the ranked station list until a tool
returns a concrete station CSV dataset/resource from a `resource_name` station
search, then stage that exact resource.

If prior structured state contains
`resource_discovery.station_resource_queries`, treat those entries as the
authoritative acquisition plan emitted by the station-catalog tool. Execute the
listed `preferred_calls` for the nearest stations in order until one returns a
concrete station CSV. Do not replace those typed calls with city-name searches,
multi-station keyword lists, or broad catalog discovery unless every preferred
call has failed or returned no station CSV. After a preferred call returns a
station CSV candidate, immediately call `ndp_stage_resource` for that returned
dataset/resource before trying another broad search.

If prior structured state already contains filtered station metadata
(`station_catalog.status=ranked_metadata_only`) plus
`resource_discovery.station_resource_queries`, do not stage or filter the
EarthScope metadata catalog again. Resume from the typed acquisition frontier:
search only the remaining ranked station IDs that are not already present in
`resource_discovery.searched_station_ids`. If
`resource_discovery.status=search_exhausted`, do not call any NDP tool. Return
the terminal metadata-only acquisition blocker, preserving `metadata_path`,
`stations`, `searched_station_ids`, `attempt_count`, and the blocker text from
typed state. Do not suggest another same-run search for a station that has
already been searched.

If an `ndp_search_datasets` observation returns `_meta.status="skipped"` with
`_meta.reason="duplicate_station_resource_search"` or
`_meta.reason="resource_discovery_search_exhausted"`, treat that observation as
authoritative typed workflow feedback. Do not issue another search for the same
station code, do not switch to a broad CSV search, and do not try a station-code
permutation. Read `clio_runtime.terminal` and
`clio_runtime.workflow_state.resource_discovery.remaining_station_ids`: if
`terminal=true` or the remaining-station list is empty, immediately return the
metadata-only acquisition blocker. If remaining station IDs are listed, search
only the next unsearched ID from that list. This rule is about workflow state,
not about specific station names; it must work for any geography.

Bound empty station-resource search loops, not only failed tool calls. After
station metadata has been spatially filtered, search the ranked station IDs
emitted by `resource_discovery.station_resource_queries` in order. If the top
five ranked station IDs, or all available ranked station IDs when fewer than
five exist, have each been searched with the preferred station-specific CSV
calls and none returned a concrete station time-series CSV, stop searching and
return structured `resource_discovery.status=search_exhausted` evidence. If a
search attempt count reaches eight after metadata filtering without a concrete
station CSV, also stop and return `search_exhausted`. Do not continue with
city-name variants, combined station-name strings, or generic
`EarthScope GNSS CSV` searches after this boundary. This is a semantic
acquisition blocker, not a user-facing final success.

Geographic provenance is mandatory. A station-specific CSV is usable for a
regional request only when its station ID matches one of the IDs returned by
`ndp_filter_earthscope_station_catalog` for the current request's latitude,
longitude, and radius, or when another tool result provides equivalent
station-coordinate evidence inside that radius. Do not stage or mark
`analysis_ready=true` for a station CSV merely because it is an EarthScope GNSS
CSV. If search returns a station CSV for a station outside the filtered station
set, keep it as negative/counterexample evidence and continue searching the
nearby station IDs; if none can be staged, return a grounded blocker instead of
an off-region analysis artifact.

For regional requests, `acquisition.analysis_ready=true` also requires
`resource_candidate.geographically_grounded=true`. Set that field only after
the selected station-specific CSV's station ID is present in the filtered
`station_catalog.stations` for the current region, or after equivalent
structured station coordinate evidence proves the station is inside the
requested radius. If the CSV stages successfully but the geographic proof is
missing or mismatched, return `acquisition.status=staged`,
`acquisition.analysis_ready=false`, and a blocker explaining the missing
filtered station metadata provenance. Do not continue the depth chain from an
ungrounded staged station CSV.

Bound failed search loops. If two consecutive `ndp_search_datasets` calls fail
after station metadata has already been staged and spatially filtered, stop
searching and return a structured blocker with
`resource_discovery.status=tool_failed`, `acquisition.status=blocked`,
`analysis_ready=false`, the exact failed tool names/arguments, and the service
error evidence. Do not keep trying broad search variants after repeated tool
failures, and do not phrase that blocker as "no station CSV exists"; phrase it
as "station-resource search failed after metadata filtering."

If `ndp_search_datasets` or `ndp_get_dataset_details` returns any concrete
station-specific CSV resource URL/name, your next tool call must be
`ndp_stage_resource` for one of those returned resources. A candidate URL,
dataset id, or resource name is not acquisition. Do not finish with
`acquisition.status=ready`, `analysis_ready=true`, or a final answer that only
lists download URLs. Finish successfully only after `ndp_stage_resource` returns
a local path for the selected station CSV.

Valid staging calls include either:

- `ndp_stage_resource(dataset_identifier="<dataset id>", resource_name="<exact returned CSV resource name>", server="global")`
- `ndp_stage_resource(dataset_identifier="<exact returned https CSV URL>", resource_name="<exact CSV filename>", server="global")`

Do not provide `max_bytes` for a selected station CSV unless the user explicitly
asked for a download limit. EarthScope station time-series CSVs can be tens of
megabytes; a small arbitrary limit turns a valid selected resource into a false
staging failure. If `ndp_stage_resource` returns a structured staging error for
the selected station CSV and the error details mention `max_bytes`,
`--max-filesize`, `resource_too_large`, or curl file-size failure, retry the
same exact dataset/resource once without `max_bytes` before searching for
another station or falling back to broad catalog discovery. Keep the retry tied
to the same selected station candidate and cite both the failed limited attempt
and the successful unrestricted attempt if it succeeds.

Stage only resources returned by `ndp_search_datasets`,
`ndp_get_dataset_details`, or another tool result. Do not construct raw CSV URLs
from station IDs or channel suffix guesses. If live station-specific search
still yields only metadata or no usable CSV, return a metadata-only acquisition
state with `resource_discovery.status=search_exhausted` and the exact searches
attempted. Do not provide `output_dir` unless the user explicitly requested one;
CLIO will default staging under the active workspace artifact root.

Return:

- selected dataset id/name/title;
- selected station id;
- resource name/index;
- `selected_resource_url` or `source_url`;
- staged local path;
- staged byte size;
- blocker code and next action if staging fails.

Path integrity is evidence integrity. Any `local_path`, `metadata_path`, or
artifact path you report must be copied exactly from the `ndp_stage_resource`
or downstream tool result. Do not rewrite workspace roots, move files from the
workspace into `$HOME`, shorten paths, or replace ASCII hyphens with Unicode
hyphen characters. If the tool returns a path under the active workspace
artifact root, report that exact path rather than relocating it to a
home-directory or process-local path.

After successful staging include parent-consumable JSON evidence:

```json
{
  "workflow_state": {
    "resource_candidate": {
      "status": "selected",
      "dataset_id": "<dataset id>",
      "dataset_name": "<dataset name>",
      "resource_name": "<resource name>",
      "resource_url": "<source URL>",
      "station_id": "<station id if known>",
      "station_distance_km": 0,
      "geographically_grounded": true
    },
    "acquisition": {
      "status": "staged",
      "analysis_ready": true,
      "local_path": "<exact staged CSV path>",
      "source_url": "<source URL>",
      "size_bytes": 0,
      "required_columns": ["time", "east", "north", "up"]
    }
  }
}
```

If the only staged file is metadata/index/catalog evidence, return:

```json
{
  "workflow_state": {
    "resource_candidate": {
      "status": "metadata_only"
    },
    "acquisition": {
      "status": "metadata_only",
      "analysis_ready": false,
      "metadata_path": "<exact staged metadata path if a tool staged one>",
      "blocker": "staged resource is station metadata, not a GNSS time-series CSV"
    },
    "resource_discovery": {
      "status": "search_exhausted",
      "searches": [],
      "blocker": "station-specific searches did not return a concrete GNSS time-series CSV"
    }
  }
}
```

If the station CSV was staged but cannot be geographically grounded for the
requested region, return:

```json
{
  "workflow_state": {
    "resource_candidate": {
      "status": "selected",
      "station_id": "<station id if known>",
      "geographically_grounded": false
    },
    "acquisition": {
      "status": "staged",
      "analysis_ready": false,
      "local_path": "<exact staged CSV path>",
      "blocker": "staged station CSV lacks geographic provenance from the filtered station metadata for the requested region"
    }
  }
}
```

If one or more station CSV candidates were found but none was staged yet,
return pending acquisition state rather than analysis-ready state:

```json
{
  "workflow_state": {
    "resource_candidate": {
      "status": "candidate_found",
      "dataset_ids": [],
      "resource_names": [],
      "resource_urls": []
    },
    "acquisition": {
      "status": "candidate_found",
      "analysis_ready": false,
      "blocker": "station CSV candidates were found but no local CSV was staged"
    },
    "resource_discovery": {
      "status": "candidate_found",
      "next_action": "call ndp_stage_resource for a returned station CSV resource"
    }
  }
}
```

If staging fails, set `acquisition.status` to `blocked` and include the tool
error code, resource URL, and next action.

If station-resource search fails before a concrete station CSV can be selected,
return:

```json
{
  "workflow_state": {
    "acquisition": {
      "status": "blocked",
      "analysis_ready": false,
      "blocker": "station-resource search failed after metadata filtering"
    },
    "resource_discovery": {
      "status": "tool_failed",
      "failed_tools": [],
      "failed_arguments": [],
      "next_action": "retry NDP station-resource search when the service is available"
    }
  }
}
```

Do not use stale local files.
