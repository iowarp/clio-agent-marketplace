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
# In-pack launch command: the implementation now lives inside this pack at
# spotter-ai/impl (git-subtree imported, full history preserved). `uv run
# --project <path> <entry>` resolves/builds that project's env on demand --
# the local-source form of the eventual `uvx spotter-ai spotter-mcp` once
# the repo is published to PyPI. See "Launch command" below for why this
# uses the mapping (command + args-list) declaration form instead of a
# single command string.
mcp_servers:
  spotter:
    command: uv
    args:
      - run
      - --project
      - ${LOCALAPPDATA}/clio-agent/agent-blueprints/spotter-ai/impl
      - spotter-mcp
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

## Launch command

Two resolution constraints, verified against `clio_agent.tools.mcp_config`
and a live spawn:

1. **No pack-relative resolution.** `mcp_servers` commands carry no
   `{pack_dir}` templating, and the spawned server's `cwd` is the active
   session's *workspace* root, not this pack's installed directory -- so a
   pack-relative path such as `./impl` or `../spotter-ai/impl` does NOT
   resolve to this pack, even though installed packs sit side-by-side
   under `agent-blueprints/`. `${VAR}` expansion against the real process
   environment IS supported, so the path anchors on `${LOCALAPPDATA}`
   (Windows per-user app-data root, where `agent-blueprints/` is
   installed) instead of a hardcoded developer path.
2. **Use the mapping form, not a single command string.** A single
   `"uv run --project ${LOCALAPPDATA}/... spotter-mcp"` string is
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
portable long-term form is `uvx spotter-ai spotter-mcp` once spotter-ai is
published to PyPI.
