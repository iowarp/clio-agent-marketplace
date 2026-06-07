---
id: earthscope-gnss-region-width
title: EarthScope GNSS Region Width Topology Agent
version: 0.1.0
description: Width-topology variant for resolving geography, discovering NDP EarthScope GNSS resources, profiling station CSV time series, and producing evidence-backed artifacts.
root_expert: main
blueprint:
  format: agent-blueprint-v1
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

# EarthScope GNSS Region Width Topology Agent

Marketplace Agent Blueprint topology variant for NDP/EarthScope meeting demos where the user
asks a natural geographic question about seismic or geodetic context in a U.S.
region. The intended first data product is NDP-listed EarthScope GNSS
station/time-series CSV evidence, not a SAC waveform, unless the user explicitly
requests waveform data.

This variant exposes geography, discovery, station catalog, resource resolver,
analysis, visualization, and synthesis as direct children of `main` to test
wide orchestration and merge quality.
