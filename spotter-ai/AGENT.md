---
id: spotter-ai
title: SPOTTER AI
display_name: SPOTTER AI (provenance investigator)
version: 0.2.0
description: Provider-aware investigation of agentic execution and artifact lineage across
  Flowcept, CMF, and documented native JSONL provenance stores.
root_expert: spotter_watcher
blueprint:
  format: agent-blueprint-v1
mcp_servers:
  spotter:
    command: uv
    args:
      - run
      - --project
      - ${LOCALAPPDATA}/clio-agent/agent-blueprints/spotter-ai/impl
      - spotter-mcp
      - --clio-config
      - ${SPOTTER_CLIO_CONFIG}
experts:
  - experts/spotter_watcher.md
---

# SPOTTER AI — provider-aware provenance investigator

SPOTTER investigates agentic execution and artifact provenance without calling back into
clio-agent. Its MCP reads the explicit CLIO YAML path in `SPOTTER_CLIO_CONFIG`, uses that file to
select the active agentic and artifact providers, and connects directly to their query stores.

The two query domains are independently configurable:

- agentic execution: Flowcept MongoDB or documented native JSONL;
- artifact lineage: CMF REST or documented native JSONL/workspace evidence.

Provider selection is configuration, never a tool argument. An unsupported operation returns a
`capability_unavailable` tool error; SPOTTER does not silently replace a Flowcept or CMF semantic
with a weaker native approximation.

This pack is an agent-facing MCP integration. gact-tui does not use it: the UI continues to call
the stable clio-agent REST resources, and clio-agent queries its configured providers for those
views.
