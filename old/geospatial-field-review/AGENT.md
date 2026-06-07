---
id: geospatial-field-review
title: Geospatial Field Review Agent
version: 0.1.0
description: Reviews GeoJSON field-site data for map-overlay and spatial-analysis readiness.
root_expert: main
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/main.md
  - experts/spatial_features.md
defaults:
  prompt_profile: heavy
---

# Geospatial Field Review Agent

A geospatial-domain agent for GeoJSON feature review. It validates marketplace
session semantics with coordinate, geometry, bounds, and property checks.
