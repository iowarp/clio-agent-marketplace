---
name: hpc-workloads
title: HPC Workloads
description: Three worked examples — LAMMPS alone, an app with the Darshan
  interceptor, and a composed pipeline whose second stage renders per-frame
  images retrieved through the artifact channel. Assumes relay-operations.md,
  jarvis-pipelines.md, and spack-slurm.md.
---

Use this skill when a request maps onto one of these three shapes: run a single
application, run an application under an I/O-tracing interceptor, or run a
composed pipeline whose second stage produces visual output you need to bring
back locally. Each example is a template, not a literal script — package names,
step ids, and settings must be confirmed live via `jarvis_describe` before use
(see `jarvis-pipelines.md`'s discovery-first guidance); this pack's own
verification could not hardcode this cluster's exact installed-package names
without running a workload, which the pack's own build was scoped not to do
(see the pack README's GAP list).

## Workload A — LAMMPS alone

The simplest shape: one package, one step, run it, confirm it finished, report
its outputs.

1. `jarvis_describe(cluster, target='package_search', query='lammps')` to
   confirm the exact installed package name.
2. `jarvis_create_pipeline(cluster, pipeline_id='lammps-run')`.
3. `jarvis_describe(cluster, target='package', package_name=<confirmed>)` to
   read its agent-visible settings (input script, working directory, MPI rank
   count, etc. — read the description, don't assume field names).
4. `jarvis_add_step(cluster, pipeline_id, package_name=<confirmed>,
   config={...})` with the settings the description named.
5. If the runtime resolves through Spack, `remote_spack_spack_locate` it first
   and copy `load_spec` into `jarvis_run`'s `spack_specs` (see
   `spack-slurm.md`); otherwise `jarvis_run(cluster, pipeline_id)` directly.
6. Poll `jarvis_get_execution(cluster, pipeline_id, execution_id)` to
   `terminal`. On success, list `artifacts={}` and report what came out
   (role, state, location) — fetch only what the request actually needs
   inspected locally.

## Workload B — an application plus the Darshan interceptor

Same shape as A, with one extra step added **before** the application step:

1. Confirm both package names: the application's (as in Workload A) and
   Darshan's, via `jarvis_describe(target='package_search', query='darshan')`.
2. `jarvis_create_pipeline`, then `jarvis_add_step` the **Darshan step first**
   (interceptor steps observe what runs after them — pipeline order is
   execution order), then `jarvis_add_step` the application step.
3. `jarvis_run`, then poll `jarvis_get_execution` to terminal exactly as in A.
4. Darshan's own output (the I/O trace/log) appears as an additional artifact
   record on the same execution — list `artifacts={}`, find the one whose
   role/location identifies it as Darshan's (its package_id filter in the
   artifact page helps here — `jarvis_get_execution(..., artifacts={package_id:
   <darshan's package alias>})`), then `relay_fetch_artifact` it and read it
   back with `fs_read_file` to report what it shows (I/O volume, access
   pattern summary — whatever the trace format actually contains; never
   summarize a trace you have not read).

## Workload C — a composed pipeline with a rendering second stage

The two-stage shape: stage one produces data, stage two consumes it and renders
per-frame images, and the images come back through the artifact channel (not a
live service — see `jarvis-pipelines.md`'s live-service-vs-artifact-files
distinction).

1. Confirm both package names — the data-producing application, and the
   rendering package (ParaView, run in an offscreen/batch mode as a pipeline
   step, is the owner's stated ideal for this stage; confirm via
   `jarvis_describe(target='package_search', query='paraview')` whether this
   cluster actually has it installed before assuming so — this pack's build
   could not verify that live; if it's absent, the GAP list in the README
   applies and the request needs a different rendering path, not an invented
   package name).
2. `jarvis_create_pipeline`, `jarvis_add_step` the data-producing step, then
   `jarvis_add_step` the rendering step configured (per its own
   `jarvis_describe(target='package')` settings) to read stage one's output and
   write per-frame image files — this is ordinary JARVIS step chaining, not a
   special "pipeline of pipelines" feature.
3. `jarvis_run`, poll `jarvis_get_execution` to terminal.
4. List `artifacts={role: 'output'}` to get the frame files' identity/location
   without their content. Fetch the frames you actually need locally with
   `relay_fetch_artifact` (one call per artifact id) — remember the transfer
   ceiling from `relay-operations.md`: a large frame or a large batch of frames
   can hit it, and an oversize one is refused rather than partially downloaded.
   Report exactly which frames you retrieved, their local paths, and their
   sizes; never claim a frame exists or looks a particular way without having
   fetched and, where the format allows, read it back.
