---
id: cluster-operator
title: Cluster Operator
display_name: Cluster Operator (HPC via clio-relay)
version: 0.1.0
description: Operates an HPC cluster through clio-relay's typed tool surface — builds
  and runs JARVIS pipelines, installs software via Spack, drives every submission to
  a terminal state, and retrieves execution artifacts. Any agent carrying this pack's
  relay tool grants plus its four skills can drive the same cluster surface the ares
  agent drives by hand. No custom MCP server: every tool this pack grants is a
  host-native relay/JARVIS/Spack tool clio-agent already mounts when relay is
  configured — this pack is grants + doctrine, not a new server.
root_expert: operator
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/operator.md
---

# Cluster Operator

The missing half of "a random agent with clio-relay and a set of skills can operate
the cluster and launch HPC applications through the clio-relay protocol." Where
`spotter-ai` watches a workload's provenance and `phenotype` runs one, this pack
*is* the workload driver: point it at an HPC cluster clio-relay has registered, and
it builds JARVIS pipelines, installs software with Spack, runs them, and reports
back with evidence.

## No mcp_servers — this pack grants, it does not launch

Unlike `spotter-ai`/`phenotype`, this AGENT.md declares no `mcp_servers` block.
The tools it grants (`jarvis_*`, `relay_*`, `remote_spack_spack_*`) are **host-native**:
clio-agent mounts them itself, once, at server boot (`clio_agent.gact.relay_wiring`
+ `clio_agent.tools.relay_factory.discover_relay_tool_surfaces`) whenever the relay
transport is configured (`relay.mcp_url` / `relay.http_url` / `CLIO_RELAY_API_TOKEN`,
etc.) — independent of any pack. This pack's only job is to *declare* the subset of
that host surface a cluster operator needs (`tools:` on `experts/operator.md`) and
to ship the doctrine (the system prompt + `skills/`) that makes an agent use it
correctly. If the live serve has no relay configured, the operator's tools are
absent and the expert is disabled with typed `unknown tool reference` diagnostics —
that is the correct, honest failure mode, not a bug in this pack.

## The relay tool ACL (14 relay tools + 1 local companion)

Every tool below is real and verified live against the operator relay door
(`clio-relay` MCP door, `tools/list`, 2026-08-18): the door serves 21 tools total,
of which clio-agent projects three families onto its own gateway namespaces:

- `jarvis` (6, from `clio_agent.tools.jarvis_jobs.JARVIS_TOOL_NAMES`) — pipeline
  authoring, already curated by clio-agent to the door's registered
  `remote_jarvis_jarvis_*` route.
- `relay` (`relay_observe`, `relay_wait`, `relay_list_artifacts`,
  `relay_read_artifact`, `relay_fetch_artifact`) — job/task follow-up, artifact
  listing (by `job_id` OR `execution_id` — clio-relay#278 made the execution id
  a first-class listing key, retiring the old guess-the-owning-job workaround),
  bounded inline reads, and bounded local transfer.
- `remote` (federated door catalog, everything prefixed `remote_`) — of which only
  the three `remote_spack_spack_*` tools have no curated clio-agent equivalent, so
  those three are the only `remote_*` tools this pack grants. (The federation also
  re-exposes `remote_jarvis_jarvis_*` redundantly; this pack does not grant those —
  use the curated `jarvis_*` six instead, see `skills/relay-operations.md`.)

The door additionally serves 9 more `relay_*` tools (`relay_remote_mcp_context`,
`relay_submit_agent`, `relay_status`, `relay_cancel`, `relay_artifact_lineage`,
`relay_queue_list`, `relay_queue_diagnose`, `relay_queue_stale`,
`relay_bind_jarvis_runtime`, `relay_storage_status`) that clio-agent's tool layer
does not project at all — this pack cannot grant what clio-agent does not expose.
See the README's GAP list.

```
jarvis_create_pipeline    jarvis_describe        jarvis_add_step
jarvis_edit_step          jarvis_run             jarvis_get_execution
relay_observe             relay_wait             relay_list_artifacts
relay_read_artifact       relay_fetch_artifact
remote_spack_spack_find   remote_spack_spack_install   remote_spack_spack_locate
fs_read_file
```

`fs_read_file` is the one non-relay addition: the only local companion the three
owner workloads need, to read back a small fetched artifact (a Darshan report, a
pipeline log tail) after `relay_fetch_artifact` lands it in the session workspace.
No `shell_bash` — this operator drives the cluster through relay's typed tools
only, never local shell.

## System prompt

The literal system prompt is `experts/operator.md`'s markdown body (the file
`parse_expert_file` compiles into the ReAct expert's instructions) — read it there,
not paraphrased here. It states: the role (HPC cluster operator via clio-relay); the
v2 task discipline (submit → wait/poll to terminal → retrieve artifacts; never
invent a result); typed-error handling (read `reason` + the message text, then
follow `skills/relay-operations.md`'s recovery table); and loud-degradation
awareness (a dev-mode deferred-enforcement record is informational, not a
blocker — the call still succeeded).

## Skills

- `skills/relay-operations.md` — the tool surface, the submit/wait/observe/cancel
  lifecycle, and the typed error recovery table. Load this first.
- `skills/jarvis-pipelines.md` — compose and run a JARVIS pipeline, including
  interceptors (Darshan) and staged local inputs.
- `skills/spack-slurm.md` — install software with Spack and select a Slurm
  execution backend through `jarvis_run`'s `execution` intent (there is no
  separate `slurm_*` tool surface).
- `skills/hpc-workloads.md` — the three worked examples: LAMMPS alone, an app with
  the Darshan interceptor, and a composed two-stage pipeline that ends in
  artifact-channel image retrieval.

See `README.md` for the pack tree, the verified ACL, and the honest GAP list of
what the real surface does not support.
