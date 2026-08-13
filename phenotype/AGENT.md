---
id: phenotype
title: Phenotype Campaign
display_name: Phenotype (synthetic workload)
version: 0.1.0
description: Synthetic plant-phenotyping campaign operator — the reference stand-in
  workload for SPOTTER AI. Runs a deterministic 5-stage pipeline (ingest ->
  calibrate -> segment -> extract traits -> predict) with full provenance capture
  per stage execution. Swap this pack for your own workflow; SPOTTER attaches the
  same way.
root_expert: main
blueprint:
  format: agent-blueprint-v1
# Demo-box launch command (direct venv exe — sandbox-friendly, no uv wrapper);
# the public form becomes `uvx spotter-ai phenotype-mcp` once the repo is published.
mcp_servers:
  workload: D:/Libraries/Documents/projects/spotter-ai/.venv/Scripts/phenotype-mcp.exe
experts:
  - experts/main.md
---

# Phenotype Campaign (synthetic workload)

Deterministic synthetic science: batches of plant sensor readings flow through
ingest -> calibrate -> segment -> extract traits -> predict, and every stage
execution is recorded to the provenance store (inputs hashed, parameters,
outputs summarized). Exists so SPOTTER AI has a workload to protect in demos —
the pipeline is real execution, only the science is synthetic.
