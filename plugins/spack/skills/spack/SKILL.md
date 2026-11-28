---
name: spack
description: Research what an HPC site already has through Spack and clio-relay, have JARVIS prepare a Spack that reuses it (`jarvis spack prepare` through relay), install the rest through jarvis install jobs, and what JARVIS's questions about MPIs and compilers mean.
keywords: [spack, hpc, mpi, jarvis, clio-relay, install, level:L2]
---

# Spack on HPC sites

This covers software on a remote HPC site reached through clio-relay, such as ParaView, an
MPI code or an I/O library.

JARVIS owns deployment on the site. It prepares its own Spack (the JARVIS Spack,
`JARVIS_SPACK_ROOT`) with `jarvis spack prepare`, and it installs with `jarvis ppl install`.
CLIO reaches both through relay, and reads the site through clio-kit's `spack_site_query`.

## What the site already has

- The site's own Spack and modules, above all its MPI, are built for the site's interconnect.
  A conda, pip or `PATH` MPI is not, and does not span nodes on its fabric. The JARVIS Spack
  reuses the site's install tree as an upstream and builds only what is missing.
- Software built by hand, private wrapper scripts, symlinks and `LD_LIBRARY_PATH` edits sit
  outside what Spack and JARVIS track; a run job gets its environment from what the install
  built (see section 3).
- Login nodes are shared, and site policies keep builds off them. The light work JARVIS does
  there is `jarvis spack prepare` (a shallow clone, configuration writes, `compiler find`,
  `external find`), `spack find`, `spack info`, `spack spec` and `module avail`; builds run as
  jarvis install jobs on compute nodes. A process left running after a command ends keeps
  running on the shared node.
- clio-relay is the site's transport (`describe`, `exec`, `files`, `run`), with the person's
  approval and the site's guard. An SSH session of your own has neither.
- `spack_find`, `spack_locate`, `spack_search` and `spack_info` look at the Spack on the
  machine the server runs on, not at a site; `spack_site_query` looks at a site.
  `spack_environment` and `spack_install` belong to the server's admin profile, not this one.

## The two-call flow (`spack_site_query`)

`spack_site_query` never touches the site itself.

1. Without `relay_result`, it returns `status: "relay_call_required"` and `relay_call`: the
   clio-relay `exec` call to make (`relay_call.arguments`: `site`, `command`, `timeout_s`,
   `max_output_bytes`).
2. That `exec` call runs with the arguments unchanged.
3. Called again with the same arguments and `relay_result` set to the `exec` structured result,
   it returns one of:
   - `"done"` with the answer;
   - `"failed"` with `error` and `stderr_tail`;
   - `"needs_approval"`: relay asked the person and could not show the ask itself. The result
     carries `ask` (`ask_id`, `message`, `page`) and the same `relay_call`; once the person has
     answered, the same `exec` call and a new `relay_result` finish it;
   - `"declined"`: the person did not approve the ask;
   - `"refused"`: relay's guard or policy refused the command.

A `relay_result` for a different argv than the one returned is rejected.

## 1. Research the site (read-only)

- clio-relay `describe` gives the site's home (`remote_dir`), whether it is guarded, and
  `facts.jarvis`: `exec`, the argv prefix that runs relay's JARVIS on the site, and
  `spack_root`, the JARVIS Spack.
- `spack_site_query` `query: "modules"` (`module -t avail`) shows what the site ships; one
  module name in `spec`, such as `openmpi` or `mpich`, narrows it.
- Once the JARVIS Spack is prepared (section 2):
  - `query: "find"`, optional `spec`: installed and upstream packages, each with `name`,
    `version`, `dag_hash`, `compiler` and `architecture`.
  - `query: "info"`, with the package name in `spec`: versions and variants.
  - `query: "spec"`, with a spec in `spec`: every node of the concretized tree with its
    `status` (`installed`, `upstream` from the site Spack, `external`, or `missing`), `counts`
    per status, and `to_build`, the missing nodes a jarvis install job would still build.
- Every call takes `site` (the relay site id) and `site_home` (relay's `remote_dir`). The
  checkout it reads defaults to `<site_home>/spack`, where relay keeps the JARVIS Spack;
  `root` overrides it when `facts.jarvis.spack_root` says otherwise.
- A `"failed"` result with `no CLIO Spack at ...` means the JARVIS Spack is not prepared yet.
- The first `spec` on a fresh JARVIS Spack downloads the clingo solver once. It is a download,
  not a build.

On a guarded site, queries run Spack directly as
`env SPACK_DISABLE_LOCAL_CONFIG=1 <spack> find|info|spec`, which is on relay's read-only list,
but only for a Spack the site's guard lists (by default the one under relay's home). The guard
is the limit the person set for the site; a `root` it does not list is `"refused"`.

## 2. Prepare the JARVIS Spack through relay

A site needs it before its first install, when an install reports `spack_missing`, or when
relay asks which Spack to use. `spack_missing` lists the site's own Spack checkouts in
`site_spacks[]`, each with its `prepare` command; relay `describe`, the modules or the site's
documentation also name the site's Spack root.

It runs with relay `exec`, as `facts.jarvis.exec` followed by JARVIS's arguments:

    <facts.jarvis.exec...> spack prepare --root <facts.jarvis.spack_root> --site_spack <site Spack root> +json

A site with no Spack takes `--spack_version <release>` instead of `--site_spack`. Other
options, rarely needed:

- `--install_tree`: the site install tree (default: asked of the site Spack);
- `--module_paths`: module directories to search for MPI modules (default: `MODULEPATH` from
  a login shell);
- `--build_tools`: build tools to register as non-buildable externals, or `none` (default: a
  fixed list; never an MPI);
- `--compiler <constraint>`: the preferred compiler, the answer to `ambiguous_compiler`;
- `--answers answers.json`: answers keyed by `issue_id`, as for `ppl install`;
- `+no_clone`: refuse instead of cloning a missing root.

On a guarded site, `exec` takes a `plan`, such as
`{"kind": "spack", "summary": "Prepare the JARVIS Spack at <root>, chained to <site Spack>"}`;
relay then asks the person itself and runs that exact argv once, for at most 900 s. A
`needs_approval` result is answered by sending the same `exec` again once the person has
answered relay's ask.

What JARVIS does:

- shallow-clones the Spack release the site runs (pinned by commit) into the root, or refuses
  when the root holds another release or is not a Spack;
- writes the root's site scope, `<root>/etc/spack`: `upstreams.yaml` at the site install tree
  (and its module trees), caches and bootstrap under `<root>/var/jarvis`, `build_jobs`, and
  concretizer reuse;
- runs `compiler find`, then registers the build tools with `external find --not-buildable`;
- sets `packages:mpi:buildable:false` and records every site MPI module as an external with its
  `prefix` and `modules`. It never externalizes an MPI from `PATH`;
- orders compilers: full toolchains (cc, cxx and fc) first, the one the upstream MPI was built
  with first among them.

It never installs or builds, and a rerun rewrites only what changed. On a site whose policy
allows nothing but `spack find` and `spack spec` on its login nodes, JARVIS runs it inside a
submitted job instead.

With `+json` the last stdout line is the `jarvis.spack-site-prep.v1` record, also kept at
`<root>/var/jarvis/site-prep.json` (`files` `op: "read"`):

- `version`, `commit`, `pinned` and `checkout` say which Spack the root holds; `site_spack` and
  `upstream_install_tree` say what it reuses.
- `module_mpis`, `mpi_externals_added` and `installed_mpis` say which MPIs the site offers;
  `compiler` says which compiler JARVIS chose and why (`chosen`, `source`, `candidates`).
  `warnings` lists anything that went wrong.
- `environment` holds `JARVIS_SPACK_ROOT`. Relay exports it into its JARVIS commands and jobs
  on the site once the root has `bin/spack`.

The exit code:

- **0**: `prepared`.
- **3**: `needs_decision`. The record's `open_issues` hold an `ambiguous_compiler` question
  whose `candidates[]` give each compiler's `constraint` and whether it built the upstream MPI
  (a compiler other than the MPI's risks an ABI mismatch). The same command with
  `--compiler <constraint>` (or `--answers`) answers it.
- **5**: a refusal (`jarvis.issue.v1`, `subject: spack_site_prep`) that changed nothing valid.
  Its `kind` says why, such as `site_spack_invalid`, `site_install_tree_invalid`,
  `spack_version_mismatch`, `spack_root_not_spack` or `build_tool_invalid`, and it names the
  argument at fault. Deleting or editing the root gets past it only by losing what the root
  holds.
- **69**: relay has not placed JARVIS on the site yet; relay installs JARVIS with its own ask.

## 3. Install through jarvis

A jarvis install job is a one-node scheduler job that builds on a compute node:

    jarvis ppl install +submit +json                          # build what is missing
    jarvis ppl install +check +submit +json                   # report only
    jarvis ppl install +submit --answers answers.json +json   # re-run with answers

jarvis resolves find-first against the JARVIS Spack named by `JARVIS_SPACK_ROOT`, so it reuses
the upstream, the externals and anything installed, and builds only what is missing. Relay
exports it into the jobs it submits; outside relay, the pipeline's scheduler `pre_cmds` set it.
On the login node, `+submit` only writes the snapshot and calls the scheduler, and
`jarvis ppl install +check` without `+submit` only runs `spack spec -I` and `spack find`.

Relay's `run` of a JARVIS package does this itself: it asks the person before it installs
anything, runs the install as its own job before the run, and turns JARVIS's questions into
asks (see the `use-relay` skill). The exit codes and issues below are what JARVIS reports either
way.

With `JARVIS_INSTALL_ON_LOAD=check` on the submitting process (or in the scheduler's
`pre_cmds`), a run job verifies its packages instead of building them, and `ppl submit` exits 3
without submitting when something is missing.

`jarvis execution get +json` follows the job. `metadata.install` reports its `phase` (`queued`,
`resolving`, `waiting_env_lock`, `building`, `needs_decision`, `refused`, `failed`, `done`) and
the paths of `install.log`, `issues.jsonl` and `install-record.json` under
`<execution>/install/`. With `+json`, the last stdout line is a `jarvis.install-report.v1`
document with `exit_code`, `issues` and `issues_path`. The exit code:

- **0**: everything is installed (`spack_site_query` `find` confirms it). A run job of the same
  pipeline loads what the install built (the lock hash) and exports the chosen MPI
  (`JARVIS_MPI_NAME`, `JARVIS_MPI_SPEC`, `JARVIS_MPI_TYPE`, `JARVIS_MPI_PREFIX`). Other Spack
  software a run needs through `jarvis_run`'s `spack_specs` is named `/<dag_hash>` from the
  site `find`, the exact form `spack_locate`'s `load_spec` gives locally; an executable path
  derived from a prefix skips what loading sets up.
- **3**: a decision is needed (`phase: needs_decision`), or `+check` found packages that still
  need building. Each question is a `jarvis.install-issue.v1` line in `issues.jsonl`, with a
  stable `issue_id` and a `kind`:
  - `ambiguous_provider`: several MPI candidates (installed, upstream or `packages.yaml`
    externals, module MPIs included), and nothing pins one. `candidates[]` gives each one's
    `id`, `constraint`, `source`, `prefix` and, for module externals, `modules`.
  - `variant_conflict`: the concretizer reports a conflict, resolved by a spec constraint
    (such as `~cuda`).
  - `concretize_failed`: any other concretizer error; `detail` holds the excerpt, and
    `spack_site_query` `spec` and `info` show the cause (another version, variant or compiler).
  - `no_recipe`: Spack has no recipe for the package. A package can add a recipe repo with
    `install_repos`, or change its `install_query`.
  - `not_installed`: `+check` found nodes still to build; an install job without `+check`
    builds them.

  Answers go into `answers.json`, keyed by `issue_id`, and the same install job resubmitted
  with `--answers answers.json` applies them:

      {"<issue_id>": {"constraint": "<one candidate's constraint>", "answered_by": "<person>"}}

  A plain string value (`{"<issue_id>": "<constraint>"}`) also works. When the issue lists
  candidates, the answer is one of their constraints. jarvis records applied answers in the
  pipeline's `install/decisions.yaml`, so later run jobs reuse them.
- **4**: `refused: build_outside_allocation`. Something tried to build outside a scheduler
  allocation, for example `ppl install` without `+submit`, or a run submitted with the default
  `JARVIS_INSTALL_ON_LOAD=install`. Nothing was built; `jarvis ppl install +submit` builds it
  in a job. `+allow_local` and `JARVIS_ALLOW_LOCAL_BUILD=1` build where the command runs,
  which on a site is the login node.
- **1**: an error, such as a failed build; the tail of `install.log` says why.

## What the person knows

Some answers depend on what only the person or the site's documentation knows: which MPI spans
nodes on the site's interconnect, which compiler toolchain the site prefers, whether a
`to_build` list is expected (a GUI stack pulled in with a visualization package), whether a
version or variant may change. A `"needs_approval"` ask is relay's and has already reached the
person, with its `message` and `page`. JARVIS has already settled the Spack release to clone,
the build-tool externals and reuse of the site upstream.

A successful `spec` or install shows the packages built, not that the scientific workflow
works; its run and results show that.
