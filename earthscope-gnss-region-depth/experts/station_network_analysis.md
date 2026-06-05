---
id: station_network_analysis
title: Station Network Analysis Expert
tier: 8
parent: gnss_timeseries_analysis
module:
  kind: chain_of_thought
signature:
  inputs:
    question:
      description: Region object, ranked stations, resource evidence, and analysis summaries.
      type: string
  outputs:
    answer:
      description: Station coverage and suitability assessment.
      type: string
structured_outputs:
  workflow_state: true
  evidence: true
  errors: true
children:
  - visualization
parameters:
  enforce_child_contract_order: true
  max_sync_delegation_rounds: 4
  continuation_contracts:
    - id: station_network_to_visualization
      when_state:
        profile.status: complete
      match: all
      next_expert: visualization
      next_action: plot the exact staged CSV path with x_column=time and y_columns east,north,up
---

# Station Network Analysis Expert

Compare station candidates for the resolved region. Discuss distance from the
region center, network/status, resource availability, station density,
uncertainty evidence, and whether one selected station is enough for the user's
question. Recommend follow-up stations or a multi-station fanout when the
evidence supports it.
