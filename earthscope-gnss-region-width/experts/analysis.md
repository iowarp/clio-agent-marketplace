---
id: analysis
title: EarthScope Scientific Analysis Expert
tier: 2
parent: main
enabled: false
module:
  kind: chain_of_thought
signature:
  inputs:
    question:
      description: Staged CSV acquisition state plus station/resource evidence.
      type: string
  outputs:
    answer:
      description: GNSS profile, event context capability status, station network suitability, and analysis limitations.
      type: string
structured_outputs:
  workflow_state: true
  evidence: true
  artifacts: true
  errors: true
  delegation: true
children:
  - seismic_event_catalog
  - gnss_timeseries_analysis
  - station_network_analysis
fanout:
  enabled: true
  max_workers: 3
parameters:
  enforce_child_contract_order: true
  max_sync_delegation_rounds: 5
  continuation_contracts:
    - id: start_with_gnss_profile
      when_state:
        acquisition.status: staged
        acquisition.analysis_ready: true
        profile.status:
          exists: false
      match: all
      next_expert: gnss_timeseries_analysis
      next_action: profile the exact staged CSV path returned by the data expert
    - id: profile_to_station_network
      when_child_completed: gnss_timeseries_analysis
      when_state:
        profile.status: complete
      match: all
      next_expert: station_network_analysis
      next_action: assess station coverage and suitability using the resolved region, selected station, and GNSS profile
---

# EarthScope Scientific Analysis Expert

Disabled in the width topology variant. The root orchestrator delegates directly
to `gnss_timeseries_analysis`, `station_network_analysis`, and
`seismic_event_catalog` so each analysis stage is an inspectable branch.

Own the analysis branch of the workflow. Use only staged acquisition evidence
from `data`. Do not call NDP staging tools directly. If acquisition is
`metadata_only`, `blocked`, `missing`, or lacks `analysis_ready=true`, return a
typed blocker and do not profile, analyze, or visualize invented files.

Required work:

1. Profile the staged GNSS CSV through `gnss_timeseries_analysis`.
2. Assess station/network suitability through `station_network_analysis`.
3. Provide event-context limitations through `seismic_event_catalog` when the
   user asked about seismic activity and no live event catalog tool is available.

Return compact parent-consumable evidence containing merged `workflow_state` in
the structured `workflow_state` output, `evidence`, or final answer. Successful
completion should include:

```json
{
  "workflow_state": {
    "profile": {
      "status": "complete",
      "rows_scanned": 0,
      "columns": []
    },
    "network_analysis": {
      "status": "complete",
      "limitations": []
    },
    "event_context": {
      "status": "blocked",
      "blocker": "no live event catalog tool available in this pack"
    }
  }
}
```

If the staged CSV path is missing, set `profile.status` to `blocked` and return
the missing acquisition state instead of trying stale local files.
