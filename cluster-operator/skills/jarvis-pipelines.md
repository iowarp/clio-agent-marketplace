---
name: jarvis-pipelines
title: JARVIS Pipelines
description: Compose and run a JARVIS pipeline through the relay's six curated
  tools, including interceptors like Darshan and staged local inputs. Assumes
  relay-operations.md.
---

Use this skill whenever the request is "run this application on the cluster,"
"add a step to a pipeline," or "attach an interceptor" — anything that composes or
executes a JARVIS pipeline rather than just installing software (that's
`spack-slurm.md`) or is one of the three reference workloads end-to-end (that's
`hpc-workloads.md`).

## What a JARVIS pipeline is

A JARVIS pipeline is an ordered list of **steps**, each backed by a **package**
(an application or interceptor JARVIS knows how to configure and run). You build
one with the six curated tools, in this order:

1. `jarvis_create_pipeline(cluster, pipeline_id)` — creates an empty, named
   pipeline and waits for the bounded deployment call.
2. For each step: first `jarvis_describe(cluster, target='package',
   package_name=...)` to read that package's **canonical setting names** and
   which ones are agent-visible — never guess a setting name or invent nesting.
   Ambiguous short names fail with the canonical candidates listed; use one of
   those. Then `jarvis_add_step(cluster, pipeline_id, package_name, config=...)`
   using only the canonical names `jarvis_describe` returned (aliases are
   accepted only when the package's own description lists them). Omit a setting
   to take its package-owned default; pass explicit `null` only for a setting
   the description marked `nullable=true`.
3. To change your mind: `jarvis_edit_step(cluster, pipeline_id, step_id,
   operation='edit', config=...)` or `operation='remove'`.
4. `jarvis_run(cluster, pipeline_id, spack_specs=..., execution=...)` starts it.
   This is handle-first (see `relay-operations.md`) — it returns
   `{task_id, job_id, pipeline_id, execution_id, ...}` immediately, before the
   workload has done any real work.
5. `jarvis_get_execution(cluster, pipeline_id, execution_id, artifacts={})`,
   polled until `terminal` is true, is how you learn what actually happened.

**Discover before you assume a package exists.** Never hardcode a package name
you have not confirmed. Use `jarvis_describe(target='package_search',
query=...)` for bounded discovery (fast, page-limited to 25) — reach for
`target='packages'` (the exhaustive full-catalog listing) only when you
genuinely need the complete inventory; it is explicitly documented as
potentially large and slow, and this pack's own live verification hit its
bounded relay-side timeout probing it. Search first.

## Interceptors (e.g. Darshan)

An interceptor is just another package added as a **step** in the same pipeline —
there is no separate interceptor API. To attach one (Darshan is the standing
example the owner names): `jarvis_describe(target='package_search',
query='darshan')` to confirm the exact package name this cluster has installed,
`jarvis_describe(target='package', package_name=<confirmed name>)` to read its
settings (typically where to write the trace/log output), then `jarvis_add_step`
it into the pipeline **before** the application step it's meant to observe —
JARVIS pipeline order is execution order. Run the pipeline exactly as any other;
the interceptor's own output (a trace or log file) shows up as an artifact record
on the SAME execution, typically with `role: "log"` or `role: "output"` — list it
with `jarvis_get_execution(..., artifacts={})` and fetch it with
`relay_fetch_artifact` like any other artifact.

## Watching the execution, not the dispatch

`jarvis_run`'s handle names the *dispatch* (did the start get admitted). The
workload's real progress is `jarvis_get_execution`'s own `state`/`terminal`
fields, polled with the `pipeline_id`/`execution_id` `jarvis_run` returned:

```
result = jarvis_run(cluster=..., pipeline_id=..., spack_specs=[...])
# result: {task_id, job_id, pipeline_id, execution_id, state:"queued", terminal:false}
loop:
    exec = jarvis_get_execution(cluster=..., pipeline_id=result.pipeline_id,
                                 execution_id=result.execution_id,
                                 include_progress=True)
    if exec.terminal: break
# exec.state is now the pipeline's real terminal state; exec.error and
# exec.return_code are populated on a FAILED execution, never fabricated.
```

Every genuinely new execution identity gets its own immutable input manifest
(JARVIS reconciles tracked local-file settings once, at that point); retrying the
same `idempotency_key` reuses that manifest rather than rescanning mutable host
files — use a stable key when you want a re-submit to be a true retry of the same
inputs, and a fresh one when the inputs have actually changed.

## Selecting where and how it runs

`jarvis_run`'s optional `execution` object selects local, cluster, or hostfile
mode and Slurm-style resource fields (`account`, `cpus_per_task`, `gpus`,
`exclusive`, ...) without exposing scheduler internals directly — this is the
full extent of Slurm control this tool surface exposes; see `spack-slurm.md` for
what that means in practice. When a step resolves its runtime through Spack,
copy `spack_locate`'s `output.load_spec` **unchanged** into one element of
`jarvis_run`'s `spack_specs` — never derive an executable path yourself from a
Spack install prefix.

## Live services vs. artifact files

`relay_bind_jarvis_runtime` (a raw door tool this pack does **not** grant — see
the pack README's GAP list) binds a *live network service* a completed execution
is running (e.g. an interactive viewer) to a local port. That is a different
thing from a pipeline step that writes output *files* — this pack's workloads
(see `hpc-workloads.md`) use the artifact-file path exclusively:
`jarvis_get_execution(..., artifacts={})` to list, `relay_fetch_artifact` to pull
bytes. If a request genuinely needs a live interactive service binding, that is
outside this pack's current tool grant — say so rather than improvising.
