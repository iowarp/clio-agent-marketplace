---
name: use-relay
title: Using relay's compute sites
description: Use this skill to run jobs, commands, file transfers or services on the person's compute sites through relay. It says how to find the sites and how to get each site's own guide.
---

# Using relay's compute sites

Relay reaches the compute sites the person has set up, such as a cluster over
SSH, a Globus Compute endpoint or a Tapis tenant. Its five verbs are
`describe`, `run`, `exec`, `files` and `serve`. Beside them, `packages` stages
the JARVIS packages `run` takes, and `shutdown` stops relay's long-lived
processes when the host closes.

## Start with describe

Call `describe` before anything else. Without arguments it lists the sites;
with `site` it describes one site and its routes. Pick a site from that list;
do not guess site names.

## Read the site's guide

A site can carry its own guide: how to submit to that machine, which
partitions and modules to use, where scratch space is. Get it from
`describe(site=...)` before the first run there. When the site has a guide,
the result has a second text block that holds it, and the site's
`skill.text` reads `(below)`. When the `skill` field says relay cannot find
the guide, tell the person; do not invent one.

A site without a guide has no second block. Work from what `describe`
reports.

Relay also serves the guides as MCP resources, `relay://sites/<site>/skill`
for a site's and `relay://skills/<name>` for each skill it knows, for clients
that read resources. They are not files: `files` refuses `relay://` URIs, so
use `describe` instead.

## Run work

- `run` submits a job as a PSI/J JobSpec. When CLIO supports tasks it returns
  a task; otherwise it waits up to `wait_s` and returns the operation, which
  `describe(job=...)` observes.
- `exec` runs one short command on the site's login side and returns bounded
  output.
- `files` lists, reads, writes and stages small files. `stage` returns the
  SHA-256 a JobSpec input names.
- `serve` starts a job with ports and returns how to reach it. Each port in
  the endpoint has an `address` (`host:port`): hand that to the client.
  To serve one package beside a run, such as pvserver beside xcompact3d, give
  both in one `serve` pipeline: set `service: true` only on the step that
  serves the ports, and place the steps on their nodes with each step's
  `host_slice` parameter (pvserver `0:2`, xcompact3d `2:6`, say).
  The other steps run alongside it in the same job.

A refusal carries a typed reason in `structuredContent.refusal`. Read it and
act on it: a site that needs sign-in, a missing account or an unreachable host
are things to tell the person, not to retry.

## Stage a package before it runs

`run` takes a JARVIS package by name, `package: {name, parameters}`, and runs
only a package relay has staged. `describe(site=...)` lists the staged ones
under `packages`; `packages(op="list")` lists them too, with where each came
from. When the package you need is not there, stage it with the `packages`
tool. Do not look for relay's files or build an archive by hand.

Stage from one of two sources:

- **Relay's package sources.** `packages(op="stage",
  package="clio_jarvis.xcompact3d")` with nothing else stages it from the
  package repositories installed beside relay. This plugin ships clio-jarvis
  at its pin, so its packages need no download, no account and no sign-in.
  The result's `sources` lists the directories relay looked in.
- **A directory on the relay host.** `packages(op="stage", package="...",
  dir="/abs/path")` stages a package from the person's workspace, such as one
  just written with the JARVIS package skill. `dir` is the JARVIS repository
  or the folder that holds it. The archive reaches the site as a job input,
  through the site's own file transfer (scp on an ssh site). Never push a
  person's package to a git repository to get it onto a site.

Give `version` only when the package has no `contract.yaml` version and no
git tag. Staging
runs nothing and touches no site: on a guarded site the person still reviews
the archive, by its SHA-256, before its first run there.

`packages(op="remove", package="...")` takes a package out of relay's
catalog, every version of it unless `version` or `sha256` narrows it. Use it
when the person resets a demo or wants an older archive gone; staging the
same files again gives the same SHA-256, so an earlier review still holds.
When several archives of one name are staged, `run` refuses and lists them:
ask the person which one and pin its `version` or `sha256`.

After a plugin update the package sources may build a new archive of a name.
A run, stage or list by name then stages it, and the older archive shows
`superseded_by`. Run the name, not the old `sha256`, unless the person asks for
that archive; a guarded site reviews the new one before it runs.

## When a site has no Spack for JARVIS

A run can refuse `adapter_unavailable` with `refusal.data.missing: "spack"`:
JARVIS needs a Spack to install the package with, and relay found none at its
CLIO Spack checkout. This is not something to tell the person and stop on.
`refusal.data.remedy` (`action: "prepare_spack"`) says what to do:

1. Use this plugin's `spack` skill and its `spack_prepare_site` tool, which come
   with relay. If they are not in the conversation, offer the `spack` plugin.
2. Call `spack_prepare_site` with `site` (the run's site), `site_home` (the
   directory above `remedy.root`; relay's default is `~/.clio-relay`) and
   `site_spack` set to `remedy.site_spacks[0].root`, the site's own Spack. The
   new checkout reuses it as an upstream; relay never builds into it. When
   `site_spacks` is empty, leave `site_spack` empty and give `spack_version`.
3. Follow the skill's two-call flow: make the `exec` call it returns, with its
   arguments unchanged. On a guarded site the person approves the plan. Then
   call `spack_prepare_site` again with `relay_result`.
4. When it returns `"done"`, call the same `run` again. Do not install anything
   on the login node: JARVIS builds what is missing in its install job, after
   relay's install ask.

Do not inspect the site by hand (`ls`, `module`) to work out the Spack: the
refusal already says what relay looked for and what the site has.

## Long runs and failed installs

An install, the queue and the run itself can take hours. When `run` or
`serve` returns a task, say what you are waiting for and end your turn: CLIO
wakes you when the task ends, so do not poll `describe` in a loop. When you are
woken, carry on with the next step of the plan the person approved.

A job that waits in the queue says so: the operation's `result.queue` (and its
message) names the partition, Slurm's `reason`, `estimated_start` and
`starts_in_s`, and `idle_partitions`, the partitions with free nodes now, each
with `fits` when the job's nodes and time would fit there. When the estimate
is far off and a partition fits, relay itself asks the person whether to keep
waiting or move the job there: the task turns `input_required` with that
choice. Relay the question as it is; relay moves the job only on the person's
answer, keeps its id, and runs the operation's later jobs on that partition.
Do not cancel and rerun to switch partitions yourself.

Leave a job's queue unset (`attributes.queue_name`, or a package's `queue`
parameter) unless the person names one: the site's `defaults.queue`, shown by
`describe(site=...)`, applies to a job with none.

An install that asks to choose an MPI asks once per site. A later install's
approval says it uses the MPI chosen for that site before; approve it to keep
that choice, and decline only when the person wants to choose again.

When a multi-node run fails and the operation's `result.mpi_network_hint` is
set, the ranks could not reach each other over TCP, usually because Open MPI
picked an interface every node shares (such as `docker0`) instead of the
fabric between them. Do not stop at the diagnosis. Compare the network relay
found, `describe(site=...)` under `info.mpi.network`, with the nodes'
interfaces (`exec` with `ip -o -4 addr` shows the login side's). Then propose
the fix to the person: write the nodes' fabric, a CIDR or interface names
joined by commas, to `mpi_network_hint.site_record` as one line
`<network> person` with `files(op="write", overwrite=true)`, which a guarded
site asks the person for, and call the same `run` again. Every later job on
the site uses it.

When an install job fails, the run fails `submit_failed` with
`refusal.data.needs: "jarvis ppl install"`. Its message ends with the last part
of the install log, and `refusal.data.install_log` is the whole log on the site:
read it with `files(op="read")`. Find the cause, fix it with the tool that owns
it, and call the same `run` again. The site's Spack configuration belongs to
the `spack` skill: when the log shows the wrong compiler, for example one with no
Fortran for a package that needs it, call `spack_prepare_site` again with
`compiler=` naming one the report lists in `compiler.toolchains`. Ask the
person only for a real decision, such as a choice between two compilers or a
larger allocation.

## Sites are the person's

Do not add, edit or remove sites. The person manages them on the Compute page
or with `clio-relay site` on the command line.
