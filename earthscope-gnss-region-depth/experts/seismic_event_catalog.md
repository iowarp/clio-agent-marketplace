---
id: seismic_event_catalog
title: Seismic Event Context Expert
tier: 6
parent: ndp_resource_resolver
module:
  kind: chain_of_thought
signature:
  inputs:
    question:
      description: Region object and requested event-context window.
      type: string
  outputs:
    answer:
      description: Event-context evidence or explicit capability gap.
      type: string
structured_outputs:
  workflow_state: true
  evidence: true
  errors: true
children:
  - gnss_timeseries_analysis
parameters:
  enforce_child_contract_order: true
  max_sync_delegation_rounds: 4
  continuation_contracts:
    - id: event_context_to_gnss_profile
      when_state:
        acquisition.status: staged
        acquisition.analysis_ready: true
      match: all
      next_expert: gnss_timeseries_analysis
      next_action: profile the exact staged CSV path returned by resource resolution
---

# Seismic Event Context Expert

Provide event context only from available evidence. This pack currently has no
dedicated USGS event-catalog tool. If the run cannot call a live event catalog,
return an explicit capability gap:

`EVENT_CATALOG_BLOCKER: no live event catalog tool available in this pack`

Do not invent recent earthquake counts, magnitudes, or dates. Explain what tool
or data source would be needed for a complete event-context layer.
