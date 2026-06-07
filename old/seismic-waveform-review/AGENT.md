---
id: seismic-waveform-review
title: Seismic Waveform Review Agent
version: 0.1.0
description: Discovers bounded seismic waveform data, inspects SAC traces, and prepares plot-ready evidence.
root_expert: main
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/main.md
  - experts/data.md
  - experts/analysis.md
  - experts/sac_format.md
  - experts/visualization.md
includes:
  - modules/ndp-collector/experts
defaults:
  prompt_profile: heavy
---

# Seismic Waveform Review Agent

A seismic-domain agent that preserves the intended hierarchy:
orchestrator to data, data to catalog child, return to data, then analysis to
SAC child, return to analysis, then visualization.

The NDP catalog child is loaded through the reusable pack-local
`modules/ndp-collector/experts` include so this pack exercises CLIO's Agent
Blueprint subtree composition semantics.
