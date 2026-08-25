---
id: earthscope-single-agent
title: EarthScope Single Agent
display_name: EarthScope Skills
version: 0.1.0
description: One persistent EarthScope GNSS agent that loads focused scientific procedures on demand, performs the work itself without child agents, and can render grounded results as an interactive A2UI analysis surface.
root_expert: main
blueprint:
  format: agent-blueprint-v1
mcp_servers:
  ndp: clio-kit mcp-server ndp
  geo: clio-kit mcp-server geo
  pandas: clio-kit mcp-server pandas
  plot: clio-kit mcp-server plot
experts:
  - experts/main.md
defaults:
  prompt_profile: heavy
workflow_state:
  sections:
    geospatial:
      status_ranks: {resolved: 4, ambiguous: 2, blocked: 1}
    catalog:
      status_ranks: {metadata_found: 4, candidates_found: 4, no_candidates: 3, blocked: 1}
    acquisition:
      status_ranks: {staged: 5, metadata_only: 4, blocked: 2, missing: 1}
      readiness:
        field: analysis_ready
        ready_status: staged
        ready_rank: 5
        requires_ondisk: true
        path_fields: [local_path, path]
        metadata_path_field: metadata_path
        demote_keep_statuses: [blocked, missing, metadata_only]
        demote_status_reused_metadata: metadata_only
        demote_status_default: candidate_found
        blocker_field: blocker
        blocker_reused_metadata: analysis-ready acquisition requires a staged station time-series resource
        blocker_default: analysis-ready acquisition requires a staged local CSV path
    station_catalog:
      status_ranks: {ranked: 4, no_candidates: 3, filter_failed: 2, blocked: 1}
    resource_candidate:
      status_ranks: {selected: 4, metadata_only: 3, blocked: 1}
      sticky_true_fields: [geographically_grounded]
    profile:
      status_ranks: {complete: 4, blocked: 1}
    visualization:
      status_ranks: {complete: 4, created: 4, blocked: 1}
    artifact:
      status_ranks: {ready: 4, complete: 4, created: 4, blocked: 1}
    presentation:
      status_ranks: {ready: 4, blocked: 1}
  artifact_paths:
    - [acquisition, local_path]
    - [visualization, path]
    - [artifact, path]
  artifact_extensions: [csv, png, md]
  aliases:
    sections: [acquisition, analysis, artifacts, dataset, evidence, geospatial, region, station_catalog]
    orphan_sections: [acquisition, analysis, artifacts, dataset, evidence, region]
    fields: [metadata_path, analysis_ready]
---

# EarthScope Skills

An intentionally single-agent EarthScope/NDP experiment. The root agent performs
the complete scientific workflow itself and loads the relevant procedural skills
only when needed. It never delegates to child agents.
