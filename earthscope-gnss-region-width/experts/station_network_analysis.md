---
id: station_network_analysis
title: Station Network Analysis Expert
tier: 2
parent: main
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
---

# Station Network Analysis Expert

Compare station candidates for the resolved region. Discuss distance from the
region center, network/status, resource availability, station density,
uncertainty evidence, and whether one selected station is enough for the user's
question. Recommend follow-up stations or a multi-station fanout when the
evidence supports it.
