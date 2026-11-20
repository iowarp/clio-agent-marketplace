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
   `max_output_bytes`).
2. Make that `exec` call with the arguments unchanged.
3. Call the tool again with the same arguments and `relay_result` set to the
   `exec` structured result. It returns `status: "done"` with the answer,
   `"failed"` with `error` and `stderr_tail`, or `"refused"` when relay refused
   the command.

Do not edit the argv. A `relay_result` for a different command is rejected.

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

The first call returns `relay_call` and `approval`. Show the person the
`approval` text, then make the `exec` call after relay's normal approval, and
call the tool again with `relay_result`.

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
error, and rerun once the cause is fixed. A `"refused"` status on a guarded
site means relay's read-only list has no `bash`, `git` or `spack`, so the CLIO
Spack cannot be prepared or queried there. Stop and tell the person. Do not
work around the guard.

## 3. Install through jarvis

Install packages only with a jarvis install job submitted to the scheduler:
`jarvis ppl install +submit`. jarvis concretizes against the CLIO Spack named by
`JARVIS_SPACK_ROOT` and `JARVIS_SPACK_CONFIG`, so it reuses the upstream and the
externals and builds only the rest, on a compute node.

When the job finishes, read its result:

- Exit code 0: confirm with `spack_site_query` `find`. Hand each package to the
  pipeline as `/<dag_hash>` in `jarvis_run`'s `spack_specs`, the same exact form
  `spack_locate`'s `load_spec` gives locally. Never pass an executable path
  derived from a prefix.
- Exit code 3: jarvis needs a decision. Read `issues.jsonl` in the job output;
  each line has a `kind`:
  - `ambiguous_provider`: several providers fit, for example several MPIs.
    Ask the person.
  - `variant_conflict`: the requested variants cannot all hold. Explain the
    conflict and ask which to keep.
  - `concretize_failed`: Spack could not solve the spec. Use `spack_site_query`
    `spec` and `info` to find the cause, propose a fix (another version,
    variant or compiler), and ask before changing the request.
  - `no_recipe`: no registered repo has the package. Say so. Do not hand-build
    it.
  - `not_installed`: a dependency is missing where it was expected. Rerun the
    install job, or report it.

  Write the person's answer into jarvis's answers (decisions) input and
  resubmit the same install job. Do not guess an answer.
- Any other non-zero exit is a build failure. Read the log tail jarvis reports,
  summarize it, and ask before trying anything different.

## 4. When to ask the person

Ask, with the options laid out, when:

- several MPIs could serve the job (`installed_mpis`, `mpi_module_candidates`,
  or an `ambiguous_provider` issue). Say which one spans nodes on the site's
  interconnect, if the site documents it.
- `spack_site_query` `spec` shows a `to_build` list the person may not expect,
  for example a GUI stack pulled in with a visualization package.
- a version or variant must change for the spec to concretize.
- the site is guarded, has no Spack and no release to pick, or relay refuses a
  step.

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
