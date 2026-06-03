---
id: format-bridge
title: Scientific Format Bridge Agent
version: 0.1.0
description: Converts scientific HDF5 datasets to downstream-readable formats with dtype policy and integrity evidence.
root_expert: main
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/main.md
  - experts/source_inspect.md
  - experts/conversion_policy.md
  - experts/lossy_policy.md
  - experts/integrity.md
  - experts/visual_check.md
defaults:
  prompt_profile: heavy
---

# Scientific Format Bridge Agent

A scientific data-engineering agent for format conversion requests where value
preservation and reviewable dtype policy matter. It inspects source data,
converts compatible columns, routes unsafe or lossy dtype cases through a
bounded policy child, verifies the output, and prepares a visualization-oriented
confirmation summary.
