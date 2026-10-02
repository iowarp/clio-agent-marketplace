---
id: appl-core
title: APPL-CORE Analyst
display_name: APPL-CORE Analyst
version: 0.2.0
description: Onboards and analyses any APPL-CORE plant-phenotyping export (an L2 agent for one export format) - reads the export's self-description, catches its data traps, records an experiment card and a saved loader next to the data, and answers phenotyping questions with evidence tagged stated, checked, or inferred.
root_expert: main
# Floor: views use the clio-workspace catalog's clio.chart.v1 presets
# (trajectories, box plots, heatmaps) and geometry-to-glb's
# clio.mesh-viewport.v1, which need clio-schemas>=0.5.1; clio-agent 0.9.4.23 is
# the first release that pins it. Older runtimes hold the pack with a typed
# blueprint_requires_newer_clio_agent instead of offering views they cannot
# render.
requires:
  clio_agent: ">=0.9.4.23"
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
plant-phenotyping facility. It works on **any** APPL-CORE export within the
supported format version, with no pack changes: per-experiment knowledge is
discovered from the export, asked of the data owners, or recorded at runtime,
never shipped here.

## Level contract

| Level | Scope | Where it lives |
| --- | --- | --- |
| L0 | any dataset: onboarding, audits, evidence tagging, 3D conversion | skills tagged `level:L0` |
| L1 | plant phenotyping at any facility: view shapes, growth, treatment response, physiology, reports | skills tagged `level:L1` (drafts) |
| L2 | the APPL-CORE export format and APPL instruments | skills tagged `level:L2` (placeholders until the falsifier experiment decides their content) |
| L3 | one experiment | **not in this pack**: the experiment card, loader, and views stored in the active workspace |

Skills hold checks and methods; facts about one experiment belong in its
card. `.lint-l3` and `lint-denylist.txt` let the marketplace linter enforce
this.

## Where L3 artefacts live

By default in the active workspace, not in the data folder:
`<workspace_root>/.clio/datasets/<key>/`, where `<key>` is the first 16 hex
characters of the SHA-256 of the export's manifest file (without a manifest:
of the resolved absolute bundle path). A second session, or the same export
mounted at another path, recomputes the key and finds the same card.

- `experiment-card.md`: facts tagged stated/checked/inferred, traps, open
  questions, proposed lessons; its frontmatter records the absolute bundle
  path, the manifest's SHA-256, and the export version.
- `loader.py`: an idempotent PEP 723 script that reads the raw files from the
  bundle root given as its argument and writes the views next to itself.
- `views/`: validated tables in the phenotyping view shapes.
- `audit/`: JSON reports from the onboarding audit scripts.

Keeping derived artefacts out of the export leaves the raw data pristine and
works with shared facility mounts; it is a default, not a restriction. The
agent passes the active workspace root to `card.py` as `--store`, and follows
the user if they want the artefacts elsewhere. What the agent may actually
write is decided by clio's permission system (approval modes, deny rules,
allowed roots, sandbox), not by this pack.
