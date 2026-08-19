---
name: spack-slurm
title: Spack + Slurm
description: Install software with Spack and select a Slurm execution backend
  through jarvis_run — there is no separate slurm_* tool surface. Assumes
  relay-operations.md.
---

Use this skill when the request is "install this package," "is X already
installed," or "run this on N nodes / with a GPU / under this Slurm account" —
anything about getting software onto the cluster or choosing how a run is
scheduled.

## There are exactly three Spack tools, and no Slurm tools at all

`remote_spack_spack_find`, `remote_spack_spack_install`,
`remote_spack_spack_locate` are the whole Spack surface this deployment
exposes. (The door registers a `clio-kit-spack-user-v2.1` compatibility
contract here — three tools; the newer `v2.3` contract adds two more that
this cluster does not yet ship. Do not assume a fourth or fifth Spack tool
exists.) **Slurm is not a separate tool surface at all** — there is no
`slurm_submit`/`slurm_status` tool. Slurm is one of the execution *backends*
`jarvis_run`'s `execution` object selects (see `jarvis-pipelines.md`): its
`account`, `cpus_per_task`, `gpus`, `exclusive`, and related fields are exactly
the Slurm-shaped knobs this tool surface exposes, without ever handing you a
raw `sbatch` invocation.

All three Spack tools are handle-first like `jarvis_run` (see
`relay-operations.md`) — each returns a queued job handle regardless of any
`wait_for_terminal` you pass; always follow up with `relay_wait(job_id=...)`.

## Checking before installing

`remote_spack_spack_find(cluster, query=...)` lists already-installed packages
matching an optional constraint. No matches is success (`count: 0`,
`packages: []`), not an error — don't treat an empty find as a failure to
diagnose. Check `find` before `install`; do not install something already
present.

## Installing

`remote_spack_spack_install(cluster, spec, reuse=True, timeout_seconds=14400)`.
`reuse` is an explicit, deliberate choice, not a default to leave unexamined:
`true` (the default) passes `--reuse` and may satisfy the spec from compatible
already-installed packages or buildcaches; `false` passes `--fresh` and
excludes them, forcing a from-scratch concretization. Prefer `reuse=True`
unless the request specifically needs an isolated rebuild. The 4-hour default
`timeout_seconds` is realistic for a real build — do not shorten it just to get
a faster-looking response; a real install can legitimately take that long, and
`relay_wait` waiting through it is the correct behavior, not a hang.

## Resolving what to run

`remote_spack_spack_locate(cluster, spec)` resolves one unique installed spec.
An absent package returns a structured `not_installed` error rather than a raw
failure — read it as "not installed," and either `find` for a close match or
`install` it. **Never derive an executable path from the returned Spack
prefix.** The only supported use of `spack_locate`'s result is to copy its
`output.load_spec` field **unchanged** into one element of `jarvis_run`'s
`spack_specs` array — JARVIS resolves that spec into a filtered runtime
environment itself. Treat `load_spec` as opaque.

## Verifying a result

After `relay_wait` reports a Spack job terminal, its result is the tool's own
structured payload (install success/failure, or the located package's fields) —
report exactly what it says. For an install, a follow-up `spack_find` with the
same constraint is the honest way to confirm it now shows up, if the request
calls for that confirmation rather than trusting the install call's own success
signal alone.

## load_spec: copy it unchanged

remote_spack_spack_locate returns `load_spec` directly under
`structured_result`. Copy that value UNCHANGED into the pipeline/step
configuration that needs the package on PATH. Live-proven failure
mode: paraphrasing or reconstructing it leaves the application off
PATH and the run fails at launch.
