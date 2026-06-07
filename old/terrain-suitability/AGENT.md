---
id: terrain-suitability
title: Terrain Suitability Agent
version: 0.1.0
description: Finds bounded DEM or lidar terrain data and derives slope/elevation suitability evidence.
root_expert: main
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/main.md
  - experts/ndp_collector.md
  - experts/terrain_derivation.md
  - experts/gridding.md
  - experts/suitability.md
  - experts/visual_summary.md
defaults:
  prompt_profile: heavy
---

# Terrain Suitability Agent

A geospatial terrain agent for site suitability studies. It coordinates data
discovery, bounded terrain staging, DEM derivation, point-cloud gridding,
constraint masking, and concise visualization summaries. It is intended for
OpenTopography/NDP-style lidar and DEM workflows where the delivered data form
is not known in advance.
