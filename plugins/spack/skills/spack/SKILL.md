---
name: spack
description: Research what an HPC site already has through Spack and clio-relay, have JARVIS prepare a Spack that reuses it (`jarvis spack prepare` through relay), install the rest through jarvis install jobs, and take choices the agent cannot resolve, such as which MPI or compiler, to the person.
keywords: [spack, hpc, mpi, jarvis, clio-relay, install, level:L2]
---

# Spack on HPC sites

Use this skill when a workflow needs software on a remote HPC site, such as
ParaView, an MPI code or an I/O library, and the site is reached only through
clio-relay. Every step happens from the conversation; nothing is set up by hand
on the cluster.

JARVIS owns deployment on the site. It prepares its own Spack (the JARVIS
Spack, `JARVIS_SPACK_ROOT`) with `jarvis spack prepare`, and it installs with
`jarvis ppl install`. CLIO reaches both through relay, and reads the site
through clio-kit's `spack_site_query`.

## Rules

- Reuse what the site already has. The site's own Spack and modules come
  first, above all its MPI, which is built for the site's interconnect. The
  JARVIS Spack builds only what is missing.
- Never hand-build software. Never use a conda or pip MPI, and never write
  private wrapper scripts, symlinks or `LD_LIBRARY_PATH` hacks. If Spack cannot
  produce it, report that and ask.
- The login node does only light, short work: `jarvis spack prepare` (a
  shallow clone, configuration writes, `compiler find`, `external find`),
  `spack find`, `spack info`, `spack spec` and `module avail`. Never run
  `spack install` or any build there, and leave no process running after a
  command ends. Builds run as jarvis install jobs on compute nodes.
- Reach the site only through clio-relay (`describe`, `exec`, `files`, `run`),
  after relay's normal approval. Do not open your own SSH session or add a
  second transport.
- Prepare a site's Spack only with `jarvis spack prepare` (step 2). Do not call
  clio-kit's `spack_prepare_site`, even if the server still lists it: JARVIS
  replaced it. Never clone Spack or write its `etc/spack` yourself.
- `spack_find`, `spack_locate`, `spack_search` and `spack_info` look at the
  Spack on the machine the server runs on, not at a site. For a site, use
  `spack_site_query`. `spack_environment` and `spack_install` belong to the
  server's admin profile, not this one. Never install with `spack_install`;
  installs are jarvis install jobs (step 3).

## The two-call flow (`spack_site_query`)

`spack_site_query` never touches the site itself.

1. Call it without `relay_result`. It returns
   `status: "relay_call_required"` and `relay_call`: the clio-relay `exec`
   call to make (`relay_call.arguments`: `site`, `command`, `timeout_s`,
   `max_output_bytes`).
2. Make that `exec` call with the arguments unchanged.
3. Call it again with the same arguments and `relay_result` set to the
   `exec` structured result. It returns one of:
   - `"done"` with the answer;
   - `"failed"` with `error` and `stderr_tail`;
   - `"needs_approval"`: relay asked the person and could not show the ask
     itself. The result carries `ask` (`ask_id`, `message`, `page`) and the
     same `relay_call`. Once the person has answered, send that `exec` call
     again unchanged, then call the tool again with the new `relay_result`;
   - `"declined"`: the person did not approve the ask. Stop; do not retry;
   - `"refused"`: relay's guard or policy refused the command. Tell the person
     and stop.

Do not edit the argv. A `relay_result` for a different command is rejected.

## 1. Research the site (read-only)

1. Run clio-relay `describe` for the site to get its home (`remote_dir`),
   whether it is guarded, and `facts.jarvis`: `exec`, the argv prefix that
   runs relay's JARVIS on the site, and `spack_root`, the JARVIS Spack.
2. See what the site ships with `spack_site_query` `query: "modules"`
   (`module -t avail`). Give one module name in `spec`, such as `openmpi` or
   `mpich`, to narrow it.
3. Once the JARVIS Spack is prepared (step 2), use:
   - `query: "find"`, optional `spec`: installed and upstream packages, each
     with `name`, `version`, `dag_hash`, `compiler` and `architecture`.
   - `query: "info"`, with the package name in `spec`: versions and variants.
   - `query: "spec"`, with a spec in `spec`: every node of the concretized tree
     with its `status` (`installed`, `upstream` from the site Spack,
     `external`, or `missing`), `counts` per status, and `to_build`, the
     missing nodes a jarvis install job would still build.
4. Pass `site` (the relay site id) and `site_home` (relay's `remote_dir`) on
   every call. The checkout `spack_site_query` reads defaults to
   `<site_home>/spack`, which is where relay keeps the JARVIS Spack; when
   `facts.jarvis.spack_root` says otherwise, pass it as `root`.
5. A `"failed"` result with `no CLIO Spack at ...` means the JARVIS Spack is
   not prepared yet: do step 2 first.
6. The first `spec` on a fresh JARVIS Spack downloads the clingo solver once.
   It is a download, not a build.

On a guarded site, queries run Spack directly as
`env SPACK_DISABLE_LOCAL_CONFIG=1 <spack> find|info|spec`, which is on relay's
read-only list, but only for a Spack the site's guard lists (by default the
one under relay's home). A `"refused"` query, for example for a `root` the
guard does not list, goes to the person. Do not work around the guard.

## 2. Prepare the JARVIS Spack through relay

Prepare it before the first install on a site, when an install reports
`spack_missing`, or when relay asks which Spack to use. `spack_missing` lists
the site's own Spack checkouts in `site_spacks[]`, each with its `prepare`
command. Otherwise find the site's Spack root from relay `describe`, the
modules, or the site's documentation; never guess a path.

Run it with relay `exec`, giving `facts.jarvis.exec` followed by JARVIS's
arguments:

    <facts.jarvis.exec...> spack prepare --root <facts.jarvis.spack_root> --site_spack <site Spack root> +json

When the site has no Spack, give `--spack_version <release>` instead of
`--site_spack`, and ask the person which release if nothing says. Other
options, rarely needed:

- `--install_tree`: the site install tree (default: asked of the site Spack);
- `--module_paths`: module directories to search for MPI modules (default:
  `MODULEPATH` from a login shell);
- `--build_tools`: build tools to register as non-buildable externals, or
  `none` (default: a fixed list; never an MPI);
- `--compiler <constraint>`: the preferred compiler, the answer to
  `ambiguous_compiler`;
- `--answers answers.json`: answers keyed by `issue_id`, as for
  `ppl install`;
- `+no_clone`: refuse instead of cloning a missing root.

The command clones and writes configuration, so ask the person before it
runs. On a guarded site, give `exec` a `plan`, such as
`{"kind": "spack", "summary": "Prepare the JARVIS Spack at <root>, chained to <site Spack>"}`;
relay then asks the person itself and runs that exact argv once, for at most
900 s. If the result is `needs_approval`, send the same `exec` again once the
person has answered relay's ask; if the person declined, stop.

What JARVIS does:

- shallow-clones the Spack release the site runs (pinned by commit) into the
  root, or refuses when the root holds another release or is not a Spack;
- writes the root's site scope, `<root>/etc/spack`: `upstreams.yaml` at the
  site install tree (and its module trees), caches and bootstrap under
  `<root>/var/jarvis`, `build_jobs`, and concretizer reuse;
- runs `compiler find`, then registers the build tools with
  `external find --not-buildable`;
- sets `packages:mpi:buildable:false` and records every site MPI module as an
  external with its `prefix` and `modules`. It never externalizes an MPI from
  `PATH`;
- orders compilers: full toolchains (cc, cxx and fc) first, the one the
  upstream MPI was built with first among them.

It never installs or builds, and a rerun rewrites only what changed. If the
site's policy allows nothing but `spack find` and `spack spec` on its login
nodes, do not run it there: tell the person, since JARVIS then runs it inside
a submitted job.

Read the result. With `+json` the last stdout line is the
`jarvis.spack-site-prep.v1` record, also kept at
`<root>/var/jarvis/site-prep.json` (read it with `files` `op: "read"`):

- `version`, `commit`, `pinned` and `checkout` say which Spack the root holds;
  `site_spack` and `upstream_install_tree` say what it reuses.
- `module_mpis`, `mpi_externals_added` and `installed_mpis` say which MPIs
  the site offers; `compiler` says which compiler JARVIS chose and why
  (`chosen`, `source`, `candidates`). `warnings` lists anything that went
  wrong.
- `environment` holds `JARVIS_SPACK_ROOT`. Relay exports it into its JARVIS
  commands and jobs on the site once the root has `bin/spack`, so there is
  nothing to set by hand.

Read the exit code:

- **0**: `prepared`.
- **3**: `needs_decision`. The record's `open_issues` hold an
  `ambiguous_compiler` question whose `candidates[]` give each compiler's
  `constraint` and whether it built the upstream MPI. Ask the person, then run
  the same command again with `--compiler <constraint>` (or `--answers`). Do
  not pick one yourself.
- **5**: a refusal (`jarvis.issue.v1`, `subject: spack_site_prep`) that changed
  nothing valid. Its `kind` says why, such as `site_spack_invalid`,
  `site_install_tree_invalid`, `spack_version_mismatch`,
  `spack_root_not_spack` or `build_tool_invalid`. Fix the argument it names,
  or tell the person; never delete or edit the root to get past it.
- **69**: relay has not placed JARVIS on the site yet. Relay installs JARVIS
  with its own ask; do not install it yourself.

## 3. Install through jarvis

Install packages only with a jarvis install job, a one-node scheduler job that
builds on a compute node:

    jarvis ppl install +submit +json                          # build what is missing
    jarvis ppl install +check +submit +json                   # report only
    jarvis ppl install +submit --answers answers.json +json   # re-run with answers

jarvis resolves find-first against the JARVIS Spack named by `JARVIS_SPACK_ROOT`,
so it reuses the upstream, the externals and anything installed, and builds
only what is missing. Relay exports it into the jobs it submits; outside relay,
set it in the pipeline's scheduler `pre_cmds`. On the login node, `+submit` only
writes the snapshot and calls the scheduler. `jarvis ppl install +check` without
`+submit` is also allowed there: it only runs `spack spec -I` and `spack find`.

Relay's `run` of a JARVIS package does this for you: it asks the person before
it installs anything, runs the install as its own job before the run, and turns
JARVIS's questions into asks (see the `use-relay` skill). The exit codes and
issues below are what JARVIS reports either way.

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

- several MPIs could serve the job (`module_mpis`, `installed_mpis`, or an
  `ambiguous_provider` issue). Say which one spans nodes on the site's
  interconnect, if the site documents it.
- several full compiler toolchains qualify (`ambiguous_compiler`).
- `spack_site_query` `spec` shows a `to_build` list the person may not expect,
  for example a GUI stack pulled in with a visualization package.
- a version or variant must change for the spec to concretize.
- the site has no Spack and no release to pick, or relay refuses a step.

A `"needs_approval"` ask is relay's, not yours: point the person to it (its
`message` and `page`) instead of asking again in your own words.

Do not ask about what JARVIS already decided: the Spack release to clone, the
build-tool externals, or reuse of the site upstream.

## 5. What not to do

- Do not call `spack_prepare_site`, clone Spack, or edit a Spack's `etc/spack`
  yourself; `jarvis spack prepare` does that.
- Do not run `spack install`, `make` or a compile on a login node.
- Do not leave background processes, daemons or `nohup` jobs on the site.
- Do not use conda or pip MPIs, or system MPIs found on PATH.
- Do not write wrapper scripts, modulefiles or symlinks by hand.
- Do not edit `~/.spack`, `~/.bashrc` or the site Spack.
- Do not treat a successful `spec` or install as proof that the scientific
  workflow works. Run the workflow and check its results.
