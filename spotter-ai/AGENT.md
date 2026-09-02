---
id: spotter-ai
title: SPOTTER AI
display_name: SPOTTER AI (forensic watcher)
version: 0.3.0
description: Live anomaly surveillance, containment, and evidence-backed provenance investigation
  across the reference phenotype campaign, Flowcept, CMF, and native stores.
root_expert: spotter_watcher
blueprint:
  format: agent-blueprint-v1
mcp_servers:
  spotter:
    command: uv
    args:
      - run
      - --project
      - ${SPOTTER_IMPL_DIR}
      - --no-sync
      - spotter-mcp
      - --clio-config
      - ${SPOTTER_CLIO_CONFIG}
experts:
  - experts/spotter_watcher.md
---

# SPOTTER AI — forensic watcher and provider-aware provenance investigator

SPOTTER investigates agentic execution and artifact provenance without calling back into
clio-agent. Its MCP reads the explicit CLIO YAML path in `SPOTTER_CLIO_CONFIG`, uses that file to
select the active agentic and artifact providers, and connects directly to their query stores.

For the reference phenotype workload, the same MCP also reads the campaign SQLite store selected
by `SPOTTER_DB`, shares the campaign identity and data directory from `SPOTTER_CAMPAIGN` and
`SPOTTER_DATA_DIR`, and owns the compatible quarantine/lift controls. These tools restore active
surveillance without replacing or weakening the provider-aware query surface.

The two query domains are independently configurable:

- agentic execution: Flowcept MongoDB or documented native JSONL;
- artifact lineage: CMF REST or documented native JSONL/workspace evidence.

Provider selection is configuration, never a tool argument. An unsupported operation returns a
`capability_unavailable` tool error; SPOTTER does not silently replace a Flowcept or CMF semantic
with a weaker native approximation.

This pack is an agent-facing MCP integration. gact-tui does not use it: the UI continues to call
the stable clio-agent REST resources, and clio-agent queries its configured providers for those
views.

Set `SPOTTER_IMPL_DIR` to this pack's absolute `impl` directory and `SPOTTER_CLIO_CONFIG` to the
CLIO YAML file. Both are explicit deployment inputs, so the same pack works on Windows and Linux.
