---
name: relay-operations
title: Relay Operations
description: The relay tool surface, the submit/wait/observe/retrieve lifecycle,
  and the typed error recovery table. Load this first — every other skill in this
  pack assumes it.
---

Use this skill before your first relay tool call in a conversation, and whenever a
tool call comes back with a typed error you don't immediately recognize. It is the
foundation `jarvis-pipelines.md`, `spack-slurm.md`, and `hpc-workloads.md` build on.

## The tool surface, grouped by what actually waits

Twelve relay tools are granted. They do not all behave the same way — knowing
which ones already wait for you and which ones hand you a bare job handle is the
single most important fact in this skill.

**Already blocking — call once, get the final result:**
`jarvis_create_pipeline`, `jarvis_describe`, `jarvis_add_step`, `jarvis_edit_step`,
`jarvis_get_execution`. Each of these drives its own dispatch to a terminal state
internally (up to ~10 minutes) before returning. There is nothing to poll for the
*dispatch* itself — but `jarvis_get_execution`'s own returned `state`/`terminal`
fields describe the *pipeline execution*, which is a separate, usually much
longer-running thing (see jarvis-pipelines.md).

**Handle-first — call, then drive to terminal yourself:**
`jarvis_run` returns `{task_id, job_id, kind:"jarvis", state:"queued",
terminal:false}` the instant the *start* is admitted, deliberately without waiting
for the workload. `remote_spack_spack_find`, `remote_spack_spack_install`, and
`remote_spack_spack_locate` behave the same way for a different reason: clio-agent's
federation projection for `remote_*` tools always returns `state:"queued"`,
`terminal:false` regardless of any `wait_for_terminal` argument you pass — the
projection layer does not read that field back off the real result. Never treat a
"queued" handle from any of these four as a finished result.

**Follow-up / retrieval, never a dispatch of their own:**
- `relay_observe` — one bounded, non-blocking read of a job's event/log cursor.
  Never blocks, never drives to terminal, safe to call as often as you like.
- `relay_wait` — observes a job for a bounded period and returns its terminal
  status if it finishes in time. If it doesn't, it returns
  `observation.outcome=observation_unknown` — **this is not a failure**, the
  underlying job is untouched and still running; call `relay_wait` again.
- `relay_fetch_artifact` — the only tool that moves bytes. Size-checked before any
  transfer starts (the smaller of this deployment's configured
  `relay.fetch_max_bytes` and relay's own hard 16 MiB per-artifact ceiling
  governs); an oversize artifact is refused from the *listing*, never
  partially downloaded. Returns `{local_path, size_bytes, sha256, origin}` —
  never the content itself. Read the file back with `fs_read_file`.

## The lifecycle: submit → wait/poll to terminal → retrieve

1. **Submit.** Call the one tool the request needs.
2. **Wait or poll to terminal, using the right handle for the right question.**
   - A Spack job handle (`job_id`): `relay_wait(job_id=...)`. It resolves a handle
     this session submitted through its own durable record; keep calling it (or
     `relay_observe` between waits) until `job.terminal` is true.
   - A `jarvis_run` handle's `task_id`/`job_id` names the **dispatch** — the fact
     that the pipeline *started*, not that it finished. To watch the actual
     execution, poll `jarvis_get_execution(pipeline_id, execution_id)` — the
     `pipeline_id`/`execution_id` your `jarvis_run` result carried — until its
     `terminal` field is true. Details in `jarvis-pipelines.md`.
3. **Retrieve artifacts, don't assume them.** `relay_list_artifacts` is the
   artifact index: pass EXACTLY ONE of `job_id` (a Spack/relay job handle) or
   `execution_id` (the id your `jarvis_run` result carried — the server resolves
   the owning job itself; works for deferred and synchronous runs alike; an
   unknown or not-yours id answers a typed `execution_not_found`, never an empty
   page). Each row carries `artifact_id`, kind, size, sha256. Then:
   `relay_read_artifact(artifact_id=...)` for a bounded inline read (small text:
   logs, reports), or `relay_fetch_artifact` only for bytes you genuinely need
   as a local file. `jarvis_get_execution(..., artifacts={})` remains the
   execution-record view (roles/state/location, content-free) — use it to
   understand an execution, and `relay_list_artifacts` to enumerate what is
   fetchable.

## The `cluster` argument

Every `jarvis_*` and `remote_spack_spack_*` tool requires `cluster`. When this
deployment has one registered (`relay.cluster` / `CLIO_RELAY_CLUSTER`), each
tool's own description states it verbatim — read the tool's description before
guessing a cluster name. Never invent one.

## The typed error recovery table

Every relay tool failure carries a `reason`. Two different layers can produce one:
clio-agent's own transport/dispatch layer (reachable directly, `reason` is exactly
what you see), and clio-relay's own door (`REASONS` registry) — which sometimes
reaches you as a directly-typed `reason`, and sometimes only as **message text**
wrapped inside a clio-agent `relay_call_rejected_inline` or `jarvis_remote_call_failed`
error. Either way: read the reason AND the message before acting — several of
clio-relay's own refusals put the actionable detail in the message, not the code.

### Table A — clio-agent's own transport/dispatch reasons

| reason | what it means | next move |
| --- | --- | --- |
| `relay_arguments_invalid` | your call's keys don't match the tool's discovered schema | the message names the exact `missing`/`unknown` keys — fix and retry |
| `relay_call_rejected_inline` / `relay_call_returned_inline` | the door answered synchronously instead of creating a durable job, often carrying a clio-relay reason as text | read the embedded message text and match it against Table B |
| `jarvis_run_wait_not_allowed` | you passed `wait`/`wait_for_terminal`/`wait_timeout_seconds`/`poll_seconds` to `jarvis_run` | drop them — `jarvis_run` is deliberately handle-first; poll `jarvis_get_execution` instead |
| `jarvis_timeout_seconds_invalid` | `timeout_seconds` wasn't a positive number | fix and retry |
| `jarvis_dispatch_timeout` | the **dispatch call itself** (not the workload) didn't finish within its ~10 min budget | retry once; a repeat means the relay-side admission path is stuck — report it |
| `jarvis_dispatch_input_required_unsupported` | the dispatch parked waiting for input this tool surface cannot answer | not retryable here — report the `task_id` and stop |
| `jarvis_remote_call_failed` | the dispatch reached JARVIS but the remote call itself failed | read `details.remote_message` (JARVIS's own error text) and correct the call — this is usually a bad config key or unsupported filter |
| `jarvis_execution_identity_mismatch` / `jarvis_execution_state_missing` | `jarvis_get_execution` returned an execution that didn't match what you asked for, or omitted state | re-issue with the exact `pipeline_id`/`execution_id` you hold on record; never substitute a guess |
| `jarvis_door_tool_not_found` | this deployment's registered door namespace doesn't match what clio-agent dispatched | a deployment configuration gap, not agent-fixable — report it verbatim |
| `jarvis_dispatch_failed` / `jarvis_dispatch_result_missing` / `jarvis_result_unwrap_failed` / `jarvis_dispatch_result_too_complex` | dispatch/transport bookkeeping failures | report the reason and state verbatim; retry once only for `jarvis_dispatch_failed` (can be transient) |
| `relay_fetch_identity_missing` | `relay_fetch_artifact` call omitted `job_id` or `artifact_id` | list artifacts first via `jarvis_get_execution(artifacts={})`, then supply both |
| `relay_fetch_artifact_not_indexed` | the `artifact_id` isn't in that job's index | re-list; use an id from `details.indexed_artifact_ids` |
| `relay_fetch_artifact_too_large` / `relay_fetch_size_unknown` | the artifact exceeds the transfer ceiling, or carries no usable recorded size | it was **not downloaded** and stays on the cluster — report the size/limit from `details`, don't retry the same call |
| `relay_fetch_size_mismatch` / `relay_fetch_digest_mismatch` | the transferred bytes didn't match relay's recorded size/digest | retry once (transient); if it recurs, report — never trust the local copy |
| `relay_fetch_target_invalid` | `target_filename` had a directory component, or was empty/`.`/`..` | pass a bare file name |
| `remote_mcp_catalog_revision_stale` | the Spack federation catalog rotated (e.g. relay redeployed) since this session started | not self-healing within the session — report it; a fresh session/turn will re-discover |
| `not_found` / `relay_task_record_missing` | the referenced job/task no longer exists or was never durable | verify the exact identity you're holding; don't guess a substitute |

### Table B — clio-relay's own `REASONS` registry

**Reachable through this pack's tools** (as a direct `reason`, or as text inside a
Table A wrapper):

| reason | what it means | next move |
| --- | --- | --- |
| `mcp_task_input_park_conflict` (retryable) | a durable task's post-admission input round lost a concurrency race | retry the same call unchanged |
| `mcp_task_conflict` | a resubmitted task identity/idempotency key collided with a different payload | mint a fresh idempotency key (or omit it) and resubmit |
| `mcp_task_status_reconciliation_failed` (retryable) | a status re-derivation failed transiently | call `relay_wait` / `jarvis_get_execution` again |
| `jarvis_dispatch_refused` | JARVIS refused the dispatch before it ever ran | `data.code`/`pipeline_id`/`execution_id` name what was refused — correct the pipeline/config, don't retry unchanged |
| `configuration_error` | broad refusal bucket | if the message starts `"contract surface unavailable: <surface> requires <need>, have <have>"` — a below-pin clio-kit build on the worker, **not agent-fixable**; report `have`/`need` verbatim and stop. Otherwise report the message verbatim, not retryable as typed |
| `storage_admission_refused` (retryable) | the cluster's storage safety boundary refused a new admission | wait and retry, or ask for less storage |
| `storage_safety_violation` | a running job already crossed a durable storage boundary | not retryable — report and stop the affected job |
| `observation_timeout` (retryable) | `relay_wait`'s bounded window expired with no state change (`observation.outcome=observation_unknown`) | **not a failure** — the job is untouched and still running; call `relay_wait` again |
| `launcher_resolution_failed` | the cluster couldn't resolve how to launch the requested step | check the step's config against `jarvis_describe(target='package')` and correct it |
| `owner_session_identity_refused` | this deployment's owner-session identity is stale/incomplete | not agent-fixable — report as a deployment gap |
| `internal_error` | unclassified server fault | retry once, then report |
| `payload_too_large` | your call's own request body exceeded the size ceiling | shrink it — page artifacts instead of inlining large config |
| `mcp_submission_conflict` | a cached admission/discovery fact you relied on went stale (live-observed on `spack_find`) | call the tool again to refresh discovery (or resubmit without any control-query evidence, as a plain workload call), then retry |

**N/A — not reachable through this pack's tools.** clio-relay's REST, browser
gateway, and WebSocket doors register the rest of the `REASONS` table:
`session_*`, `gateway_*`, `websocket_*`, `browser_*`, `route_not_found`,
`method_not_allowed`, `framework_http_error`, `input_ingest_*`, `transform_*`,
`retention_conflict`, `queue_operation_conflict`, `job_submission_*`,
`job_route_refused`, `job_cluster_mismatch`, `mcp_admission_refused`,
`jarvis_submission_refused`, `jarvis_artifact_conflict`,
`jarvis_runtime_authority_*`, `wait_parameters_invalid`, `queue_query_refused`,
`request_validation_failed`, `poll_interval_invalid`, `log_stream_invalid`,
`authentication_required`. If a failure you actually see doesn't match Table A or
Table B's reachable rows, it is not one of these — do not diagnose against this
list; report the raw reason and message instead.

## Dev-mode is loud, not blocking

clio-relay's contract gate can run in a loud-and-non-blocking mode: a below-pin MCP
surface still **serves** the call, and only logs a structured
`SurfaceContractDegradation` record (`enforcement: "deferred_dev_mode"`) on the
server side. You never see this as a tool failure. If a call succeeded, trust its
result regardless of what the server logged about it — only the `configuration_error`
/ `"contract surface unavailable: ..."` message in Table B means enforcement was
actually on and the call was refused.
