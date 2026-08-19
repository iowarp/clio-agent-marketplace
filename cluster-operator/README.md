# cluster-operator

The missing half of the crown scenario: "a random agent with clio-relay and a set
of skills can operate the cluster and launch HPC applications through the
clio-relay protocol." This pack is grants + doctrine, not a new server — every
tool it grants is a host-native relay/JARVIS/Spack tool clio-agent already mounts
when relay is configured (`clio_agent.gact.relay_wiring`,
`clio_agent.tools.relay_factory.discover_relay_tool_surfaces`). No `mcp_servers`
block, unlike `spotter-ai`/`phenotype`.

## Pack tree

```
cluster-operator/
├── AGENT.md                       # blueprint manifest (root_expert: operator)
├── README.md                      # this file
├── experts/
│   └── operator.md                # the single react expert — literal system prompt
└── skills/
    ├── relay-operations.md        # tool surface + submit/wait/retrieve lifecycle
    │                               #   + the typed error recovery table
    ├── jarvis-pipelines.md        # compose/run a JARVIS pipeline, interceptors,
    │                               #   staged inputs
    ├── spack-slurm.md             # Spack install + Slurm via jarvis_run.execution
    └── hpc-workloads.md           # the three owner workloads, worked examples
```

## The ACL (verified live against the relay door, 2026-08-18)

The door (`http://127.0.0.1:18795/mcp`, cluster `ares-p5run2`) serves 21 tools
total. clio-agent projects three families onto its own gateway namespaces
(`jarvis`, `relay`, `remote`); this pack grants 12 of the projected tools plus
one local companion:

| granted tool | namespace | door-side origin |
| --- | --- | --- |
| `jarvis_create_pipeline` | `jarvis` (curated) | `remote_jarvis_jarvis_create_pipeline` |
| `jarvis_describe` | `jarvis` (curated) | `remote_jarvis_jarvis_describe` |
| `jarvis_add_step` | `jarvis` (curated) | `remote_jarvis_jarvis_add_step` |
| `jarvis_edit_step` | `jarvis` (curated) | `remote_jarvis_jarvis_edit_step` |
| `jarvis_run` | `jarvis` (curated) | `remote_jarvis_jarvis_run` |
| `jarvis_get_execution` | `jarvis` (curated) | `remote_jarvis_jarvis_get_execution` |
| `relay_observe` | `relay` (follow) | `relay_observe` |
| `relay_wait` | `relay` (follow) | `relay_wait` |
| `relay_fetch_artifact` | `relay` (clio-agent's own, #1200) | n/a — local bounded transfer over the HTTP artifact door |
| `remote_spack_spack_find` | `remote` (federated) | `remote_spack_spack_find` |
| `remote_spack_spack_install` | `remote` (federated) | `remote_spack_spack_install` |
| `remote_spack_spack_locate` | `remote` (federated) | `remote_spack_spack_locate` |
| `fs_read_file` | built-in | n/a — reads a `relay_fetch_artifact` local copy back |

The federated `remote` namespace also re-exposes the six `remote_jarvis_jarvis_*`
tools redundantly (same underlying door route as the curated `jarvis_*` six).
This pack does not grant those — the curated `jarvis_*` names are the intended
surface (matching clio-agent's own tool-curation doctrine); granting both would
just give the model two names for the same six operations.

## What the door exposes that this pack does NOT grant (and why)

Nine more `relay_*` tools exist on the door that clio-agent's tool layer does not
project onto any gateway namespace at all — this pack cannot grant what clio-agent
does not expose as a callable tool:

- `relay_remote_mcp_context` — catalog introspection, used internally by
  clio-agent's own federation discovery, not exposed to agents.
- `relay_submit_agent` — spawns a *remote agent* on the cluster (the mechanism
  behind `relay:<cluster>` spawn placement, `clio_agent.gact.agents.spawn_placement`);
  a different capability (agent-on-cluster, not tool-on-cluster) outside this
  pack's scope.
- `relay_status`, `relay_cancel` — raw job-level status/cancel; this pack's
  workloads only ever need `relay_wait`/`relay_observe` to watch a job it just
  submitted, and JARVIS-level execution status/cancellation flows through
  `jarvis_get_execution`/pipeline editing instead.
- `relay_artifact_lineage`, `relay_queue_list`, `relay_queue_diagnose`,
  `relay_queue_stale`, `relay_storage_status` — cluster-operator-console-grade
  diagnostics, not needed by the three owner workloads.
- `relay_bind_jarvis_runtime` — binds a *live network service* (e.g. an
  interactive viewer) a completed execution is running to a local port. The
  owner's stated ParaView workload (workload C) is framed as artifact-file
  retrieval (per-frame images), not a live service, so this pack does not grant
  it; see `skills/jarvis-pipelines.md`'s live-service-vs-artifact-files note.

If a future request genuinely needs one of these, it is a scope decision for a
follow-up slice, not something to fake with the current grant.

## GAP list — real limits of the verified surface

- **Slurm has no dedicated tool surface.** There is no `clio-kit-slurm-user-v3`
  (or any) `slurm_*` remote MCP contract registered on this deployment's
  `RemoteMcpContract` enum — only `clio-kit-jarvis-user-v3.{6,7}` and
  `clio-kit-spack-user-v2.{1,2.3}` are. Slurm execution is selected entirely
  through `jarvis_run`'s `execution` intent object (`account`, `cpus_per_task`,
  `gpus`, `exclusive`, ...); `skills/spack-slurm.md` documents this as the real
  (and only) Slurm surface rather than inventing separate tools.
- **This cluster runs the Spack `v2.1` compatibility contract, not `v2.3`.**
  Live `tools/list` shows exactly the 3 `v2.1` tools (`spack_find`/`install`/
  `locate`); `v2.3`'s 2 additional tools are not present on this deployment.
  `skills/spack-slurm.md` documents 3 tools, not 5, on that basis.
- **No live-confirmed package catalog.** This build's verification calls to
  `jarvis_describe(target='package_search', ...)` against the live `ares-p5run2`
  cluster did not return within the relay's own bounded observation window
  (repeated `: ping` SSE keep-alives, no terminal result, across three attempts —
  `packages` and a bounded `package_search` alike). Rather than hardcode
  unverified package names for LAMMPS, Darshan, or ParaView,
  `skills/hpc-workloads.md` is written discovery-first: every worked example
  confirms the exact package name via `jarvis_describe` before using it, and
  says explicitly that ParaView's presence on this cluster is unconfirmed. This
  is the intentionally correct behavior per the tool's own description
  ("target='packages' ... can be large; use it only when the complete installed
  catalog is explicitly required" / "target='package_search' for bounded
  discovery") — not a workaround for the timeout.
- **No artifact-content preview tool.** `relay_fetch_artifact` returns a local
  path, never content; `jarvis_get_execution`'s artifact page is content-free
  unless `content_max_bytes` is set for `role='log'` artifacts, which requires
  `clio-kit-jarvis-user-v3.7` (this cluster is at `v3.6` per the live
  catalog-revision probe — confirm live before relying on that filter).
- **Static/offline marketplace validation will flag this pack's tool references
  as unknown.** `scripts/validate_marketplace_blueprints.py` calls
  `validate_agent_blueprint_path` with no live app, which resolves
  `runtime_tool_names_for_validation` to an empty set (by design —
  `clio_agent.gact.agent_blueprints.runtime_tool_names_for_validation`'s own
  docstring: "valid ONLY against the live runtime"). Every `jarvis_*`/`relay_*`/
  `remote_*` reference in `experts/operator.md` will show `unknown tool
  reference` under that static check. This is expected, not a defect — this
  pack was verified by binding it to a live serve instead (see below), which is
  the only correct way to validate a host-native relay tool grant.

## Serve-binding verification (2026-08-18)

Performed against the live clio-agent serve on `127.0.0.1:17900` (already
running relay-configured against `ares-p5run2`), without touching any cluster
workload:

1. Copied `cluster-operator/` into the serve's installed blueprints root
   (`%LOCALAPPDATA%\clio-agent\agent-blueprints\cluster-operator\` — the same
   root `spotter-ai`/`phenotype`/etc. already live in). `GET
   /v1/agent-blueprints` performs a fresh on-disk scan on every call
   (`discover_agent_blueprints`, no cache — read from source, not assumed) —
   the pack appeared immediately: the listing went from 10 to 11 blueprints,
   `cluster-operator` among them, no restart or "touch the exe" step needed on
   this server build.
2. `GET /v1/agent-blueprints/cluster-operator` resolved the full agent
   hierarchy: `agent_blueprint.enabled: true`, one agent row (`operator`,
   `enabled: true`, `validation_errors: []`) — confirming the live runtime's
   relay tool catalog satisfied every `jarvis_*`/`relay_*`/
   `remote_spack_spack_*` reference in `tools:`.
3. Created a scratch session (`POST /v1/sessions` → `sess_0bb8ac231bd4`) and
   bound the blueprint (`POST /v1/sessions/{sid}/agent-blueprint
   {"blueprint_id":"cluster-operator"}`); `GET
   /v1/sessions/{sid}/agent-blueprint` echoed back
   `active_agent_blueprint_id: "cluster-operator"` with the same
   zero-error agent hierarchy attached.
4. `GET /v1/agents/operator?session_id=sess_0bb8ac231bd4` — the session-scoped
   agent-resolution route — returned the operator expert's fully resolved ACL:

   ```
   tools: [jarvis_create_pipeline, jarvis_describe, jarvis_add_step,
           jarvis_edit_step, jarvis_run, jarvis_get_execution,
           relay_observe, relay_wait, relay_fetch_artifact,
           remote_spack_spack_find, remote_spack_spack_install,
           remote_spack_spack_locate, fs_read_file]
   skills: [relay-operations, jarvis-pipelines, spack-slurm, hpc-workloads]
   validation_errors: []
   enabled: true
   ```

   All 13 declared tools and all 4 declared skills resolved clean against the
   live runtime — this is "blueprint binds + tools granted + skills served."
5. Deleted the scratch session (`DELETE /v1/sessions/sess_0bb8ac231bd4`)
   afterward.

Verification stopped there, per scope: no cluster workload (LAMMPS, Spack
install, or otherwise) was run under this pack. The ares agent owns the cluster.
