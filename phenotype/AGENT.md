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
# In-pack launch command: this pack shares the spotter-ai implementation,
# imported at spotter-ai/impl (git-subtree, full history preserved). `uv
# run --project <path> <entry>` resolves/builds that project's env on
# demand -- the local-source form of the eventual `uvx spotter-ai
# phenotype-mcp` once the repo is published to PyPI. See "Launch command"
# below for why this uses the mapping (command + args-list) declaration
# form instead of a single command string, and why the path is
# `${LOCALAPPDATA}`-anchored rather than a pack-relative `../spotter-ai/impl`
# hop.
mcp_servers:
  phenotype:
    command: uv
    args:
      - run
      - --project
      - ${LOCALAPPDATA}/clio-agent/agent-blueprints/spotter-ai/impl
      - phenotype-mcp
experts:
  - experts/main.md
---

# Phenotype Campaign (synthetic workload)

Deterministic synthetic science: batches of plant sensor readings flow through
ingest -> calibrate -> segment -> extract traits -> predict, and every stage
execution is recorded to the provenance store (inputs hashed, parameters,
outputs summarized). Exists so SPOTTER AI has a workload to protect in demos —
the pipeline is real execution, only the science is synthetic.

## Launch command

Installed packs land side-by-side under `agent-blueprints/`, so
`../spotter-ai/impl` looks like it should reach the shared implementation
from here. It does not, for two verified reasons (see
`clio_agent.tools.mcp_config` and a live spawn test):

1. **No pack-relative resolution.** `mcp_servers` commands carry no
   `{pack_dir}` templating, and the spawned server's `cwd` is the active
   *session's workspace* root, not this pack's installed directory -- so
   a pack-relative path does not resolve to this pack. `${VAR}` expansion
   against the real process environment IS supported, so the path anchors
   on `${LOCALAPPDATA}` (Windows per-user app-data root, where
   `agent-blueprints/` is installed) instead of a hardcoded developer path
   or a non-resolving relative hop.
2. **Use the mapping form, not a single command string.** A single
   `"uv run --project ${LOCALAPPDATA}/... phenotype-mcp"` string is
   `shlex.split` after `${VAR}` expansion -- and `shlex` (POSIX mode)
   treats backslashes as escape characters, silently eating the
   backslashes in `${LOCALAPPDATA}`'s native Windows form
   (`C:\Users\...`) before the path ever reaches `uv`, breaking the spawn
   (confirmed live: `uv` received a corrupted path with the separators
   stripped). The mapping form (`command:` + `args:` as a YAML list, used
   above) expands each argv element independently and skips `shlex`
   entirely, so the backslashes survive intact.

This is Windows-specific; a cross-platform pack would need an OS-neutral
override (e.g. a `CLIO_USER_DIR`-style var) once one exists. The fully
portable long-term form is `uvx spotter-ai phenotype-mcp` once spotter-ai is
published to PyPI.
