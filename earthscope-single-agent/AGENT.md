---
id: earthscope-single-agent
title: EarthScope Skills
display_name: EarthScope Skills
version: 0.3.1
description: An EarthScope GNSS scientist that loads focused procedures on demand, presents grounded interactive views when useful, and may fan out independent regional work into temporary child turns.
root_expert: main
# A2UI catalogs are a per-agent allowlist, in preference order: this agent
# may produce surfaces only against the catalogs listed here (nothing is
# implicit, the builtins included). The builtin clio-workspace catalog comes
# first -- it is the general default for tables, charts, metrics, and maps --
# then the pack's own earthscope-stations catalog, whose station views name
# that catalog explicitly (the generated catalog skill states its catalogId
# and that it is not this agent's default).
a2ui_catalogs:
  - clio-workspace
  - earthscope-stations: catalogs/earthscope-stations
# Floor: clio-agent 0.9.4.17 is the first release that reads the list form
# above (and the per-agent allowlist it expresses); earlier releases would
# silently drop the pack catalog. Enforced as a typed
# blueprint_requires_newer_clio_agent at validate/activation/install.
requires:
  clio_agent: ">=0.9.4.17"
blueprint:
  format: agent-blueprint-v1
# clio-kit is provisioned once via `uv tool install clio-kit==2.10.6` (see clio-agent install/doctor).
# Installed-tool launchers replace `uvx clio-kit@...`: concurrent uvx spawns raced on a cold
# uv cache (truncated pyvenv.cfg -> dead transport -> _UnsupportedSessionAgent), and
# `uv cache prune/clean` deletes ephemeral envs under RUNNING servers (astral-sh/uv#11694).
mcp_servers:
  ndp:
    command: clio-kit
    args: [mcp-server, ndp]
    probe_timeout_retries: 10
  geo:
    command: clio-kit
    args: [mcp-server, geo]
    probe_timeout_retries: 10
  pandas:
    command: clio-kit
    args: [mcp-server, pandas]
    probe_timeout_retries: 10
  plot:
    command: clio-kit
    args: [mcp-server, plot]
    probe_timeout_retries: 10
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

An EarthScope/NDP scientist backed by focused procedural skills. The scientist
normally keeps the workflow coherent in one conversation and may create temporary
self-directed children when independent work genuinely benefits from parallelism.
