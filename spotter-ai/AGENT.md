---
id: spotter-ai
title: SPOTTER AI
display_name: SPOTTER AI (forensic watcher)
version: 0.1.0
description: Agentic forensic provenance surveillance. Attach to any session via the
  spotter-ai execution mode; SPOTTER watches the workload's provenance store, detects
  anomalous runs, quarantines the campaign, attributes the root cause by backward
  lineage traversal, and discusses the evidence on demand. Detection and attribution
  ship today; remediation semantics arrive in a later phase.
root_expert: spotter_watcher
blueprint:
  format: agent-blueprint-v1
# Demo-box launch command (direct venv exe — sandbox-friendly, no uv wrapper);
# the public form becomes `uvx spotter-ai spotter-mcp` once the repo is published.
mcp_servers:
  spotter: D:/Libraries/Documents/projects/spotter-ai/.venv/Scripts/spotter-mcp.exe
experts:
  - experts/spotter_watcher.md
---

# SPOTTER AI — forensic provenance watcher

Generic surveillance-and-attribution agent. It is workload-agnostic: any pipeline
that records its stage executions into the provenance store SPOTTER's tools read
can be watched, quarantined, and forensically attributed. The `phenotype` pack is
the reference synthetic workload; swap it for your own.

Selected not from the agent picker but from the session's execution-mode pill
(`spotter-ai`): the platform spawns this agent as a background watcher child of
the session being protected.
