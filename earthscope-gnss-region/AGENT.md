---
id: earthscope-gnss-region
title: EarthScope GNSS Region Agent
version: 0.1.0
description: Resolves a requested geography, discovers NDP EarthScope GNSS resources, profiles station CSV time series, and produces evidence-backed artifacts.
root_expert: main
blueprint:
  format: agent-blueprint-v1
mcp_servers:
  ndp: uvx clio-kit@2.2.2 mcp-server ndp
  geo: uvx clio-kit@2.2.2 mcp-server geo
  pandas: uvx clio-kit@2.2.2 mcp-server pandas
  plot: uvx clio-kit@2.2.2 mcp-server plot
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
  - experts/synthesis.md
defaults:
  prompt_profile: heavy
---

# EarthScope GNSS Region Agent

Marketplace Agent Blueprint for NDP/EarthScope meeting demos where the user
asks a natural geographic question about seismic or geodetic context in a U.S.
region. The intended first data product is NDP-listed EarthScope GNSS
station/time-series CSV evidence, not a SAC waveform, unless the user explicitly
requests waveform data.
