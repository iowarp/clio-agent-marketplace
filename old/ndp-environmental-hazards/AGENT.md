---
id: ndp-environmental-hazards
title: NDP Environmental Hazards Agent
version: 0.1.0
description: Discovers live NDP hazard datasets, queries geospatial services, profiles weather CSVs, and produces verified artifacts.
root_expert: main
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/main.md
  - experts/catalog.md
  - experts/geospatial.md
  - experts/weather_analysis.md
  - experts/visualization.md
defaults:
  prompt_profile: heavy
---

# NDP Environmental Hazards Agent

Marketplace Agent Blueprint for NDP meeting demos that need live catalog
discovery, ArcGIS FeatureServer queries, staged weather CSV analysis, and
artifact-producing visual checks.
