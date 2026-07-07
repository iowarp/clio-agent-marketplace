---
id: data-semantics
title: Data Semantics Agent
version: 0.1.0
description: Interprets scientific datasets by combining metadata inspection, semantic analysis, visualization planning, and HDF5/clio-core ingest guidance.
default_expert: main
mcp_servers:
  hdf5: uvx clio-kit@2.2.3 mcp-server hdf5
experts:
  - experts/main.md
  - experts/data.md
  - experts/analysis.md
  - experts/visualization.md
  - experts/hdf5.md
defaults:
  prompt_profile: heavy
---

# Data Semantics Agent

This Agent Blueprint is a starter marketplace package for validating CLIO's
file-backed Agent runtime. It keeps the hierarchy small enough for smoke tests
while exercising model defaults, prompts, skills, tools, and parent/child expert
links.
