---
id: materials-crystal-review
title: Materials Crystal Review Agent
version: 0.1.0
description: Reviews CIF crystal structures for structure provenance and simulation readiness.
root_expert: main
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/main.md
  - experts/crystal_structure.md
  - experts/symmetry_quality.md
  - experts/simulation_readiness.md
defaults:
  prompt_profile: heavy
---

# Materials Crystal Review Agent

A materials-domain agent for CIF review. It separates structure inspection,
symmetry/occupancy quality, and simulation-readiness synthesis so marketplace
activation covers a nested hierarchy and a domain tool surface that differs
from genomics and geospatial agents.
