---
id: spotter-ai
title: SPOTTER AI
display_name: SPOTTER AI (forensic watcher)
version: 0.4.0
description: Live anomaly surveillance, containment, and evidence-backed provenance investigation
  across the reference phenotype campaign, Flowcept, CMF, and native stores.
root_expert: spotter_watcher
# The MCP launcher reads ${CLIO_BLUEPRINT_DIR} and ${CLIO_PROVENANCE_CONFIG}, which
# clio-agent supplies from 0.9.4.19 (#1503); an older runtime holds this pack
# with blueprint_requires_newer_clio_agent instead of arming it half-configured.
requires:
  clio_agent: ">=0.9.4.19"
# A2UI catalogs are a per-agent allowlist: from clio-agent 0.9.4.17 this
# agent may produce surfaces only against the catalogs listed here, in this
# preference order (nothing is implicit, the builtins included). An older
# runtime reads a builtins-only list as no pack catalogs and still offers its
# builtins (the clio-agent floor below is for the MCP launcher, not catalogs).
a2ui_catalogs:
  - clio-workspace
blueprint:
  format: agent-blueprint-v1
mcp_servers:
  spotter:
    command: uv
    args:
      - run
      - --project
      - ${CLIO_BLUEPRINT_DIR}/impl
      - spotter-mcp
      - --clio-config
      - ${CLIO_PROVENANCE_CONFIG}
experts:
  - experts/spotter_watcher.md
---

# SPOTTER AI — forensic watcher and provider-aware provenance investigator

SPOTTER investigates agentic execution and artifact provenance without calling back into
clio-agent. Its MCP reads one explicit CLIO YAML file (`--clio-config`), uses that file to select
the active agentic and artifact providers, and connects directly to their query stores.

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

Both launcher inputs are supplied by clio-agent, so the pack arms on a normal install on Windows
and Linux with no deployment variables: `${CLIO_BLUEPRINT_DIR}` is this pack's installed directory
(the launcher runs its `impl` project), and `${CLIO_PROVENANCE_CONFIG}` is a CLIO YAML file carrying
clio-agent's effective provenance configuration (native journal by default; Flowcept and CMF when
configured). When that configuration gives SPOTTER no store to read, clio-agent refuses to arm it
and says what to enable.
