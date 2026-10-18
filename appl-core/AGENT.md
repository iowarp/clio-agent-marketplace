---
id: appl-core
title: APPL-CORE Analyst
display_name: APPL-CORE Analyst
version: 0.2.5
description: Investigates APPL-CORE plant-phenotyping data from its actual files, adapts queries and code to messy read-only inputs, and answers with source evidence, checked calculations and explicit uncertainty. Bundled scripts and schemas are optional examples.
root_expert: main
# CLIO beta 3 supplies the canonical workspace-state directory used by this
# pack's generated cards, loaders, audits and views. Older runtimes hold the
# pack with blueprint_requires_newer_clio_agent instead of starting without
# that required workspace handoff.
requires:
  clio_agent: ">=0.9.5b3"
# A2UI catalogs are a per-agent allowlist: builtin catalogs only. The level
# contract keeps UI generic -- this pack contributes no catalog of its own.
a2ui_catalogs:
  - clio-workspace
blueprint:
  format: agent-blueprint-v1
# clio-kit is provisioned once via `uv tool install clio-kit` (see clio-agent
# install/doctor). Declaration is the enablement for these tool namespaces.
mcp_servers:
  pandas:
    command: clio-kit
    args: [mcp-server, pandas]
    probe_timeout_retries: 10
  parquet:
    command: clio-kit
    args: [mcp-server, parquet]
    probe_timeout_retries: 10
  plot:
    command: clio-kit
    args: [mcp-server, plot]
    probe_timeout_retries: 10
  web:
    command: clio-kit
    args: [mcp-server, web]
    probe_timeout_retries: 10
experts:
  - experts/main.md
defaults:
  prompt_profile: heavy
---

# APPL-CORE Analyst

An analyst for exports of APPL-CORE, the processing pipeline of an automated
plant-phenotyping facility. It investigates **any** supplied APPL-CORE export,
adapting to observed structure and available tools: per-experiment knowledge is
discovered from the export, asked of the data owners, or recorded at runtime,
never shipped here.

## Level contract

| Level | Scope | Where it lives |
| --- | --- | --- |
| L0 | any dataset: onboarding, audits, evidence tagging, 3D conversion | skills tagged `level:L0` |
| L1 | plant phenotyping at any facility: identities, design, growth, treatment response, physiology, reports | skills tagged `level:L1` |
| L2 | the APPL-CORE export format and APPL instruments | skills tagged `level:L2` (placeholders until the falsifier experiment decides their content) |
| L3 | one experiment | **not in this pack**: source-backed findings, analysis code and optional derived outputs in the active workspace |

Skills hold checks and methods; facts about one experiment belong in its
card. `.lint-l3` and `lint-denylist.txt` let the marketplace linter enforce
this.

## Where L3 artefacts live

In the active workspace's namespaced Agent state, outside the data folder:
`<workspace_state>/datasets/<key>/`, where `<key>` is the first 16 hex
characters of the SHA-256 of the export's manifest file (without a manifest:
of the resolved absolute bundle path). A second session, or the same export
mounted at another path, recomputes the key and finds the same card.

- `experiment-card.md`: facts tagged stated/checked/inferred, traps, open
  questions, proposed lessons; its frontmatter records the absolute bundle
  path, the manifest's SHA-256, and the export version.
- Optional analysis code, which may be a small query, script or notebook. A
  reusable `loader.py` is one choice when repeated transformations are useful.
- Optional derived tables or views, shaped for the actual question and data.
- Optional audit reports from selected bundled tools or equivalent checks.

Treat the export as read-only input, even if a development copy is writable.
Keep derived artefacts outside it and adapt the analysis rather than repairing
the source. A fixed loader or the five example schemas is not an analysis gate. The
shell supplies `CLIO_AGENT_WORKSPACE_STATE_DIR` from the owning CLIO's path resolver;
`card.py` uses that automatically even when its working directory changes.
Standalone callers may explicitly supply an absolute state directory with `--store`.
Never create workspace `.clio` or automatically move legacy cards. CLIO's
permissions determine available output locations. A separate source-editing
task needs explicit authorization; exploration and analysis do not imply it.
