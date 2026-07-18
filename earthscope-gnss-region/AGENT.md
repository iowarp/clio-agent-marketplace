---
id: earthscope-gnss-region
title: EarthScope
display_name: EarthScope
version: 0.1.0
description: Resolves a requested geography, discovers NDP EarthScope GNSS resources, profiles station CSV time series, and produces evidence-backed artifacts.
root_expert: main
blueprint:
  format: agent-blueprint-v1
# clio-kit is provisioned once via `uv tool install clio-kit==2.2.3` (see clio-agent install/doctor).
# Installed-tool launchers replace `uvx clio-kit@...`: concurrent uvx spawns raced on a cold
# uv cache (truncated pyvenv.cfg -> dead transport -> _UnsupportedSessionAgent), and
# `uv cache prune/clean` deletes ephemeral envs under RUNNING servers (astral-sh/uv#11694).
mcp_servers:
  ndp: clio-kit mcp-server ndp
  geo: clio-kit mcp-server geo
  pandas: clio-kit mcp-server pandas
  plot: clio-kit mcp-server plot
experts:
  - experts/main.md
  - experts/geospatial.md
  - experts/data.md
  - experts/analysis.md
  - experts/ndp_dataset_discovery.md
  - experts/earthscope_station_catalog.md
  - experts/ndp_resource_resolver.md
  - experts/seismic_event_catalog.md
  - experts/gnss_timeseries_analysis.md
  - experts/station_network_analysis.md
  - experts/visualization.md
defaults:
  prompt_profile: heavy
workflow_state:
  sections:
    acquisition:
      status_ranks: {staged: 4, metadata_only: 3, blocked: 2, missing: 2}
      readiness:
        field: analysis_ready
        ready_status: staged
        ready_rank: 5
        requires_ondisk: true
        not_on_disk_rank: 1
        path_fields: [local_path, path]
        metadata_path_field: metadata_path
        demote_keep_statuses: [blocked, missing, metadata_only]
        demote_status_reused_metadata: metadata_only
        demote_status_default: candidate_found
        blocker_field: blocker
        blocker_reused_metadata: >-
          analysis-ready acquisition requires a staged data resource distinct
          from the discovery metadata catalog
        blocker_default: analysis-ready acquisition requires a staged local CSV path
    resource_candidate:
      status_ranks: {selected: 4, metadata_only: 3, missing: 2, blocked: 2}
      sticky_true_fields: [geographically_grounded]
    profile:
      status_ranks: {complete: 4, completed: 4, created: 4, plotted: 4, blocked: 2, missing: 2}
    visualization:
      status_ranks: {complete: 4, completed: 4, created: 4, plotted: 4, blocked: 2, missing: 2}
    artifact:
      status_ranks: {complete: 4, completed: 4, created: 4, plotted: 4, blocked: 2, missing: 2}
    network_analysis:
      status_ranks: {complete: 4, completed: 4, created: 4, plotted: 4, blocked: 2, missing: 2}
    catalog:
      status_ranks: {candidates_found: 3, metadata_found: 3, search_incomplete: 2, no_candidates: 2, blocked: 2}
    resource_discovery:
      status_ranks: {resource_found: 4, candidate_found: 4, search_required: 3, search_exhausted: 2, blocked: 2}
  artifact_paths:
    - [acquisition, local_path]
    - [artifact, path]
    - [visualization, path]
    - [visualization, plot_path]
    - [visualization, staged_plot_png]
    - [profile, path]
  artifact_extensions: [csv, png]
  aliases:
    sections: [acquisition, analysis, artifacts, dataset, datasets, evidence, geospatial, region, station_catalog]
    orphan_sections: [acquisition, analysis, artifacts, dataset, datasets, evidence, region]
    fields: [metadata_path, analysis_ready]
    fence_labels: [region]
  resume_example_fields: [acquisition.metadata_path, station_catalog.station_ids, acquisition.status, profile.status]
  failure_rules:
    - section: acquisition
      when: readiness_not_true
      set_status: blocked
      set_readiness_false: true
      set_fields:
        blocker: "child expert {child!r} failed before completing acquisition: {error}"
    - section: resource_discovery
      when: always
      set_status: child_failed
      set_fields:
        blocker: "child expert {child!r} failed before completing resource discovery"
        next_action: retry the child expert after provider availability is restored
---

# EarthScope GNSS Region Agent

Marketplace Agent Blueprint for NDP/EarthScope meeting demos where the user
asks a natural geographic question about seismic or geodetic context in a U.S.
region. The intended first data product is NDP-listed EarthScope GNSS
station/time-series CSV evidence, not a SAC waveform, unless the user explicitly
requests waveform data.
