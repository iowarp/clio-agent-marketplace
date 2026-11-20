---
name: spack
description: Research what an HPC site already has through Spack and clio-relay, prepare a CLIO Spack that reuses it, install the rest through jarvis install jobs, and take choices the agent cannot resolve, such as which MPI, to the person.
keywords: [spack, hpc, mpi, jarvis, clio-relay, install, level:L2]
---

# Spack on HPC sites

Use this skill when a workflow needs software on a remote HPC site, such as
ParaView, an MPI code or an I/O library, and the site is reached only through
clio-relay. Every step happens from the conversation; nothing is set up by hand
on the cluster.

## Rules

- Reuse what the site already has. The site's own Spack and modules come
  first, above all its MPI, which is built for the site's interconnect. The
  CLIO Spack builds only what is missing.
- Never hand-build software. Never use a conda or pip MPI, and never write
  private wrapper scripts, symlinks or `LD_LIBRARY_PATH` hacks. If Spack cannot
  produce it, report that and ask.
- The login node does only light, short work: `git clone`, writing config,
  `spack compiler find`, `spack external find`, `spack find`, `spack info`,
  `spack spec` and `module avail`. Never run `spack install` or any build there,
  and leave no process running after a command ends. Builds run as jarvis
  install jobs on compute nodes.
- Reach the site only through clio-relay (`describe`, `exec`, `files`), after
  relay's normal approval. Do not open your own SSH session or add a second
  transport.
- `spack_find`, `spack_locate`, `spack_search` and `spack_info` look at the
  Spack on the machine the server runs on, not at a site. For a site, use
  `spack_site_query`. `spack_environment` and `spack_install` belong to the
  server's admin profile, not this one. Never install with `spack_install`;
  installs are jarvis install jobs (step 3).

## The two-call flow

`spack_prepare_site` and `spack_site_query` never touch the site themselves.

1. Call the tool without `relay_result`. It returns
   `status: "relay_call_required"` and `relay_call`: the clio-relay `exec`
   call to make (`relay_call.arguments`: `site`, `command`, `timeout_s`,
   `max_output_bytes`, and for `spack_prepare_site` a `plan`).
2. Make that `exec` call with the arguments unchanged.
3. Call the tool again with the same arguments and `relay_result` set to the
   `exec` structured result. It returns one of:
   - `"done"` with the answer;
   - `"failed"` with `error` and `stderr_tail`;
   - `"needs_approval"`: relay asked the person to approve the plan and could
     not show the ask itself. The result carries `ask` (`ask_id`, `message`,
     `page`) and the same `relay_call`. Once the person has answered, send that
     `exec` call again unchanged, then call the tool again with the new
     `relay_result`;
   - `"declined"`: the person did not approve the ask. Stop; do not retry;
   - `"refused"`: relay's guard or policy refused the command. Tell the person
     and stop.

Do not edit the argv or the plan. A `relay_result` for a different command is
rejected.

## 1. Research the site (read-only)

1. Run clio-relay `describe` for the site to get its CLIO home (`remote_dir`),
   whether it is guarded, and what relay reports about Spack and jarvis.
2. See what the site ships with `spack_site_query` `query: "modules"`
   (`module -t avail`). Give one module name in `spec`, such as `openmpi` or
   `mpich`, to narrow it.
3. Once a CLIO Spack exists (step 2), use:
   - `query: "find"`, optional `spec`: installed and upstream packages, each
     with `name`, `version`, `dag_hash`, `compiler` and `architecture`.
   - `query: "info"`, with the package name in `spec`: versions and variants.
   - `query: "spec"`, with a spec in `spec`: every node of the concretized tree
     with its `status` (`installed`, `upstream` from the site Spack,
     `external`, or `missing`), `counts` per status, and `to_build`, the
     missing nodes a jarvis install job would still build.
4. Pass `site` (the relay site id) and `site_home` (relay's `remote_dir`; it
   defaults to `~/.clio-relay`) on every call. `root` overrides the CLIO Spack
   checkout, which defaults to `<site_home>/spack`.
5. The first `spec` on a fresh CLIO Spack downloads the clingo solver once. It
   is a download, not a build.

## 2. Prepare the CLIO Spack (one approval)

Call `spack_prepare_site` with `site`, `site_home` and `site_spack`, the site's
own Spack root (find it from relay `describe`, the modules, or the site's
documentation). When the site has no Spack, leave `site_spack` empty and give
`spack_version` instead. Optional arguments, rarely needed: `spack_version`
(default: the site Spack's release), `site_install_tree` (default: asked of the
site Spack), `module_paths` (default: `MODULEPATH`), `build_tools` (default: a
fixed list; never an MPI) and `root`.

The first call returns `relay_call` and `approval`. Its `exec` arguments carry
`plan: {kind: "spack", summary: "Prepare the CLIO Spack ..."}` and a 900 s
timeout. On a guarded site, relay asks the person to approve that plan itself;
on any other site, show the person the `approval` text first. Make the `exec`
call with the arguments unchanged, and call the tool again with
`relay_result`. If it returns `"needs_approval"`, resend the same `exec` once
the person has answered the ask; if `"declined"`, stop.

The tool:

- shallow-clones the Spack release the site runs (pinned by commit) into
  `<site_home>/spack`;
- points `upstreams.yaml` at the site install tree and turns on concretizer
  reuse;
- runs `compiler find`;
- registers build tools with `external find --not-buildable`;
- sets `packages:mpi:buildable:false`;
- records module-only MPIs as candidate externals. It never externalizes an MPI
  from PATH.

Config lives in the checkout's `etc/spack` and caches under its `var/clio`.
`SPACK_DISABLE_LOCAL_CONFIG=1` and `SPACK_USER_CONFIG_PATH=<site_home>/spack-config`
keep the person's `~/.spack` out. The tool is idempotent: a rerun reports
`clone: "present"` and an empty `config_changes`. It never installs or builds
anything, and it does not install jarvis-cd; relay bootstraps jarvis after its
own ask.

Read `report`:

- `spack_version`, `commit` and `pinned` say which Spack was cloned; `upstream`
  is the site install tree it reuses.
- `compilers`, `externals`, `installed_mpis` (MPIs already in the upstream and
  CLIO install trees) and `mpi_module_candidates` (module-only MPIs) say what
  the site offers. `warnings` lists anything that went wrong.
- `jarvis.environment` holds `JARVIS_SPACK_ROOT=<site_home>/spack` and
  `JARVIS_SPACK_CONFIG=<site_home>/spack-config`. Export both into jarvis install
  and run jobs on the site; relay exports them once the checkout and config
  directory exist.

A `"failed"` status changed nothing that needs undoing: show the person the
error, and rerun once the cause is fixed. On a guarded site, research queries
run Spack directly as `env SPACK_DISABLE_LOCAL_CONFIG=1 <spack> find|info|spec`,
which is on relay's read-only list, but only for the Spack its guard lists
(default `.clio-relay/spack/bin/spack`, the default `root`). Preparing needs the
approved plan. A `"refused"` status means the guard or policy refused the
command anyway, for example a `root` the guard does not list. Stop and tell the
person. Do not work around the guard.

A `spack_site_query` that returns `"failed"` with `no CLIO Spack at ...` means
the site has no CLIO Spack yet: run `spack_prepare_site` first.

## 3. Install through jarvis

Install packages only with a jarvis install job, a one-node scheduler job that
builds on a compute node:

    jarvis ppl install +submit +json                          # build what is missing
    jarvis ppl install +check +submit +json                   # report only
    jarvis ppl install +submit --answers answers.json +json   # re-run with answers

jarvis resolves find-first against the CLIO Spack named by `JARVIS_SPACK_ROOT`
and `JARVIS_SPACK_CONFIG`, so it reuses the upstream, the externals and anything
installed, and builds only what is missing. Both variables reach the job through
the scheduler's environment export; if the site exports nothing, set them in the
pipeline's scheduler `pre_cmds`. On the login node, `+submit` only writes the
snapshot and calls the scheduler. `jarvis ppl install +check` without `+submit`
is also allowed there: it only runs `spack spec -I` and `spack find`.

Submit run jobs with `JARVIS_INSTALL_ON_LOAD=check` set on the submitting
process (or in the scheduler's `pre_cmds`). A run job then verifies its packages
instead of building them, and `ppl submit` exits 3 without submitting when
something is missing. Install first, then run.

Follow the job with `jarvis execution get +json`. `metadata.install` reports
its `phase` (`queued`, `resolving`, `waiting_env_lock`, `building`,
`needs_decision`, `refused`, `failed`, `done`) and the paths of `install.log`,
`issues.jsonl` and `install-record.json` under `<execution>/install/`. With
`+json`, the last stdout line is a `jarvis.install-report.v1` document with
`exit_code`, `issues` and `issues_path`. Read the exit code:

- **0**: everything is installed. Confirm with `spack_site_query` `find` if you
  need to. A run job of the same pipeline loads what the install built (the
  lock hash) and exports the chosen MPI (`JARVIS_MPI_NAME`, `JARVIS_MPI_SPEC`,
  `JARVIS_MPI_TYPE`, `JARVIS_MPI_PREFIX`), so there is nothing to copy. When a
  run also needs other Spack software through `jarvis_run`'s `spack_specs`,
  pass `/<dag_hash>` from the site `find`, the exact form `spack_locate`'s
  `load_spec` gives locally. Never pass an executable path derived from a prefix.
- **3**: a decision is needed (`phase: needs_decision`), or `+check` found
  packages that still need building. Each question is a
  `jarvis.install-issue.v1` line in `issues.jsonl`, with a stable `issue_id`
  and a `kind`:
  - `ambiguous_provider`: several MPI candidates (installed, upstream or
    `packages.yaml` externals, module MPIs included), and nothing pins one.
    `candidates[]` gives each one's `id`, `constraint`, `source`, `prefix` and,
    for module externals, `modules`. Ask the person which to use.
  - `variant_conflict`: the concretizer reports a conflict. Explain it and ask
    which spec constraint to apply (such as `~cuda`).
  - `concretize_failed`: any other concretizer error; `detail` holds the
    excerpt. Use `spack_site_query` `spec` and `info` to find the cause, propose
    a constraint (another version, variant or compiler), and ask before
    applying it.
  - `no_recipe`: Spack has no recipe for the package. Not answerable: say so,
    and do not hand-build it. A package can add a recipe repo with
    `install_repos`, or change its `install_query`.
  - `not_installed`: `+check` found nodes still to build. Not a question: run
    the install job without `+check`.

  Write the person's answers into `answers.json`, keyed by `issue_id`, then
  resubmit the same install job with `--answers answers.json`:

      {"<issue_id>": {"constraint": "<one candidate's constraint>", "answered_by": "<person>"}}

  A plain string value (`{"<issue_id>": "<constraint>"}`) also works. When the
  issue lists candidates, the answer must be one of their constraints. jarvis
  records applied answers in the pipeline's `install/decisions.yaml`, so later
  run jobs reuse them. Never guess an answer.
- **4**: `refused: build_outside_allocation`. Something tried to build outside
  a scheduler allocation, for example `ppl install` without `+submit`, or a run
  submitted with the default `JARVIS_INSTALL_ON_LOAD=install`. Nothing was
  built. Resubmit as `jarvis ppl install +submit`. Do not opt out with
  `+allow_local` or `JARVIS_ALLOW_LOCAL_BUILD=1` on a site.
- **1**: an error, such as a failed build. Read the tail of `install.log`,
  summarize it, and ask before trying anything different.

## 4. When to ask the person

Ask, with the options laid out, when:

- several MPIs could serve the job (`installed_mpis`, `mpi_module_candidates`,
  or an `ambiguous_provider` issue). Say which one spans nodes on the site's
  interconnect, if the site documents it.
- `spack_site_query` `spec` shows a `to_build` list the person may not expect,
  for example a GUI stack pulled in with a visualization package.
- a version or variant must change for the spec to concretize.
- the site has no Spack and no release to pick, or relay refuses a step.

A `"needs_approval"` ask is relay's, not yours: point the person to it (its
`message` and `page`) instead of asking again in your own words.

Do not ask about what the tools already decided: the Spack release to clone,
the build-tool externals, or reuse of the site upstream.

## 5. What not to do

- Do not run `spack install`, `make` or a compile on a login node.
- Do not leave background processes, daemons or `nohup` jobs on the site.
- Do not use conda or pip MPIs, or system MPIs found on PATH.
- Do not write wrapper scripts, modulefiles or symlinks by hand.
- Do not edit `~/.spack`, `~/.bashrc` or the site Spack.
- Do not treat a successful `spec` or install as proof that the scientific
  workflow works. Run the workflow and check its results.
