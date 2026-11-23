# Changelog

## [Unreleased]

### Added

- `cad` (0.1.0): parametric CAD with the `cadquery` skill. The part is a script
  run on CLIO's own uv and Python with `cadquery>=2.8`, whose cadquery-ocp has
  wheels for Python 3.11 to 3.14, so the first run resolves on a 3.14 CLIO Python
  where an older pin such as 2.6.1 does not. It exports STEP and an STL that is
  read back and checked for watertightness and dimensions before a solver uses it.
- `clio-relay` (1.6.16): relay's MCP server, run with `uvx` from a pinned commit of
  iowarp/clio-relay, and its Compute page in CLIO's left bar, where a person sets
  the protocol and security for new endpoints, then adds, probes, edits and removes
  compute endpoints and changes each one's protocol and security in place. It
  declares the page with `navigation`, its breadcrumb title "Relay" with `title`, a
  Globus account, whose grant file it hands relay as `CLIO_RELAY_GRANT_FILE_GLOBUS`,
  and sign-in pages on the loopback address and `https://tacc.tapis.io`. It ships
  the `clio-relay-compute` A2UI catalog (the Basic components it uses plus
  `clio.choice-table.v1` for the endpoint table) and the `use-relay` skill. The
  layout check now accepts the `navigation`, `title`, `tabs`, `accounts` and
  `elicitation` host fields.
- `spack` (1.0.1): HPC software on clio-relay sites through clio-kit's spack
  server (contract `clio-kit-spack-user-v3`), run with `uvx` from a pinned commit
  of iowarp/clio-kit until clio-kit releases 3.0.0, with the `spack` skill. Research the
  site with `spack_site_query` (find, info, spec, modules), prepare a CLIO Spack
  that reuses the site's Spack as an upstream with `spack_prepare_site`, and
  install through `jarvis ppl install +submit` jobs on compute nodes, never on the
  login node. Choices the agent cannot resolve, such as several MPIs, go to the
  person. On a guarded site, queries use relay's read-only Spack argv and
  preparing goes through relay's plan ask (`needs_approval`, `declined`).

- `home-assistant` (1.0.0): Home Assistant as one plugin. It follows CLIO's
  `home-assistant` connector (ha-mcp) and brings `home-assistant-sensors` (reading
  sensors and their history, acting on devices, changing configuration deliberately)
  and `home-assistant-best-practices`, vendored unchanged from homeassistant-ai/skills
  at `166defa5` (MIT) with `import-lock.json` and
  `scripts/import_home_assistant_skills.py`.
- `barebone` (1.0.0): the model alone. With CLIO's `Agent.bare` its requests carry no
  system prompt, no tools and no context injections, so its input is exactly the
  conversation; for attention attribution (SPOTTER-AI) and small local models.

### Changed

- `clio-relay` (1.6.42) runs relay 2.0.0a1, a pre-release cut at e35f5ce2 plus a lighter
  CLI import, from its released wheel instead of a git pin. The server is a hash-locked
  project in `server/` (its one dependency is the release wheel, `no-build`, with
  atomicwrites held at 1.4.0, the last release with a wheel) started with
  `uv run --project ${PLUGIN_ROOT}/server --frozen --no-dev`, so a first launch does no
  git fetch, no source build and no resolve. It still bundles clio-jarvis ee210630.

- `spack` (1.0.4) runs clio-kit's spack server from the `spack-mcp-v1.0.0` release
  wheel, built at `ef42fcf3`, through the same hash-locked `server/` project and
  `uv run --frozen --no-dev` form, so a first launch no longer fetches the clio-kit
  monorepo.
- `clio-relay` (1.6.41) runs relay e35f5ce2 with jarvis-cd a28999b1 and still bundles
  clio-jarvis ee210630. A service's card is now bound like a run's: JARVIS plans the
  full service job, with the connector and the service's parameters, and the card shows
  its batch script. The start submits that same script, so the yes binds to it. Per-start
  secrets stay out of the sealed job.

- `clio-relay` (1.6.40) runs relay 0889629b with jarvis-cd a28999b1 and still bundles
  clio-jarvis ee210630. A guarded `serve` no longer fails before submission with
  "validation errors for JobSpec". Its card shows JARVIS's plan of the service's job,
  with its components and advisories, but no batch script, because relay adds the
  service's connector when it starts it.

- `clio-relay` (1.6.39) runs relay bee13a84 with jarvis-cd a28999b1 and still bundles
  clio-jarvis ee210630. The job card's `started_at` is the scheduler's start of the
  job itself, not of an install before it; components carry the package's name
  (gray_scott, not `pkg`); and JARVIS's advisories, such as a launch over TCP
  because UCX could not be verified, show on the card and in the confirm. A site
  that linked a retired skill (`ares`) no longer shows a broken skill link.

- `cad` (0.1.1): the `cadquery` skill hands the part over. Once its checks pass,
  the STL and the STEP are registered with `create_artifact` as deliverables, with
  the script in `used`, so CLIO opens them in its 3D view; a solver-frame copy is
  registered as intermediate. `geometry-to-glb` is only for meshes with fields.

- `clio-relay` (1.6.38) runs relay 77a49109 with jarvis-cd 3b651c68 and still bundles
  clio-jarvis ee210630. `run`, `serve` and `exec` declare that they confirm
  themselves (`io.iowarp/confirm`), so a host that leaves the confirm to relay
  shows the person one form per call. Each job travels as one typed snapshot
  (`io.iowarp.clio-relay/job`) on the confirm, the task status, the tool results
  and `describe`'s job list, for a host to draw as the job's card. For a package
  run the card is JARVIS's own plan of the submit (directives, components with
  their nodes, couplings and the script), the submit is bound to it, and a plan
  that changed after the yes is shown again rather than submitted; each
  component's state comes from JARVIS while the job runs.

- `clio-relay` (1.6.37) runs relay 5fe5e6a9 with jarvis-cd acbf4308 and still bundles
  clio-jarvis ee210630. Runs write under the site's outputs directory
  (`~/clio-relay-runs` unless set), outside relay's own, so `site clean` keeps
  them unless the person asks, and relay names a run's outputs where they live; a job naming a path inside relay's directory is
  refused. A confirm that names relay's or JARVIS's facts is a typed choice, so a
  host still asks it; a plain yes/no only confirms the call's own arguments. A
  new job on a site where another of relay's services still runs asks whether to
  end it when the job is submitted. JARVIS asks where installs check and build
  once per site, for every package. The use-relay skill puts run outputs under
  `describe`'s `outputs_dir` and says a start from nothing forgets JARVIS's
  answers.
- `clio-relay` (1.6.36) runs relay 49cf7e02 with jarvis-cd 58cd5b1a and still bundles
  clio-jarvis ee210630. Where JARVIS builds is now offered like where it checks:
  relay sets no build default, so a new site shows JARVIS's recommendation, and
  a build the person places on the login node runs JARVIS's own install there
  under JARVIS's limits, as a background task with no time limit that only the
  person cancels. Listing the staged packages is its own read-only tool,
  `packages_read`, so it works in plan mode; `packages` only stages and removes.
  The use-relay skill covers both.
- `clio-relay` (1.6.35) runs relay adbf2ff0 with jarvis-cd 58cd5b1a and still bundles
  clio-jarvis ee210630. JARVIS now asks once per site where its software checks
  and builds run (the login node under its limits, a compute job, or each
  time), with its recommendation and evidence, and relay passes the question on
  as it is. A served view reaches CLIO within seconds of being ready, a compute
  node's host key is read reliably, and a forward whose key or job is gone
  stops and says why. A site clean names the outputs its runs wrote and keeps
  them unless the person asks. The use-relay skill covers all of it and leaves
  pvserver's linger at its default.
- `clio-relay` (1.6.34) runs relay 9a748fc5 with jarvis-cd 0fa2b312 and bundles
  clio-jarvis ee210630 (pvserver stays up for a while after its last client
  leaves). No Spack runs on a site's login node any more: JARVIS checks a
  site's software in a short job on the compute nodes and keeps a record that
  later installs and runs read, so the login node only reads that record. Files
  move by path, and an install of a plan's packages takes one call with one
  review. The use-relay skill covers all of it.
- `clio-relay` (1.6.33) runs relay 9791465e with jarvis-cd 5a58ab82 and bundles
  clio-jarvis b37fb115 (xcompact3d and pvserver 0.3.7, gray_scott 0.2.3: a new
  output shows on the JARVIS node while the solver runs). A serve call now hands
  back the endpoint as soon as the service is ready, while its job keeps running.
  An install asks for approval only when JARVIS finds software missing; a site
  that has it all answers just JARVIS's questions. Installs on one site share one
  answer to a site question such as which MPI, and `site_clean` keeps JARVIS's
  answers unless asked to forget them. `site_clean` refuses while relay's jobs
  still run on the site, naming them, and a new `clio-relay cancel` command
  cancels an operation. JARVIS now locks its decision store and probes the build
  host's compilers before the first build. The use-relay skill covers all of it.
- `clio-relay` (1.6.32) runs relay 13e19b1b. Installs started at the same time on
  one site no longer race: they share one jarvis-cd ask, the second jarvis-cd
  install waits for the first and reuses it, and an answer or a decline applies to
  every install waiting on it. Package builds share JARVIS's and Spack's locks.
- `clio-relay` (1.6.31) runs relay f1749784. A new `install` tool installs a
  package's software on a site ahead of any run: JARVIS checks the site, the person
  gets the same asks as a run's install, and JARVIS builds it in a job on the
  compute nodes with nothing launched after it. A site without JARVIS gets relay's
  jarvis-cd first, after a yes. The use-relay skill says when to use it.
- `clio-relay` (1.6.30) runs relay b85d756b. A port forward to a running service
  now outlives a restart of the relay MCP server: the forward is its own process,
  and a relay that starts adopts it, or opens it again at once if it died, without
  waiting for a tool call. A command on an ssh site now returns when it exits on
  the site, even when a leftover process keeps the ssh session open.
- `clio-relay` (1.6.29) runs relay 2de1b1b6 with jarvis-cd 2d26101c and bundles
  clio-jarvis 1be94889: xcompact3d 0.3.5 (archive sha256 c59b4cbf), pvserver
  0.3.6 (f7a30fc9) and gray_scott 0.2.2 (dd9ec4c9). A background service stops
  when the pipeline's last step returns unless the person keeps it (`after_steps`,
  default auto), and JARVIS reuses its Spack load capture in check mode too.
  Relay already keeps that capture per set of packages under the site home
  (`JARVIS_SPACK_ENV_DIR`), shared by every check, submit, install and run of
  them. pvserver's `pvserver-launch.json` is now JARVIS's own `launch_record()`,
  so a launch's site-fact advisories and their `reason_codes` reach CLIO as
  JARVIS wrote them, in the log and in a start failure.
- `clio-relay` (1.6.28) bundles clio-jarvis 05d0d1a2: xcompact3d 0.3.5 (archive
  sha256 549f4905), pvserver 0.3.5 (f601c4fb) and gray_scott 0.2.2 (6bd9faea).
  xcompact3d's sizing text never rescales seconds per step to another grid. The
  `use-relay` skill's "Ask for enough time" takes seconds per step only from a
  run at production's own grid and decomposition. It never rescales a pilot's
  figure to another grid or rank count, and it re-pilots or re-measures when
  production's grid or decomposition differs from the pilot or changes after
  it, before applying the coefficient.
- `clio-relay` (1.6.27) runs relay 06a14cd4 with jarvis-cd d9cb80b6 and bundles
  clio-jarvis 161c2a89: xcompact3d 0.3.5 (archive sha256 96f2a2cb), pvserver
  0.3.5 (b18118f8) and gray_scott 0.2.2 (f1a2a9ef). JARVIS places ranks by the
  allocation's geometry and reports `phase_timings`, and the packages' time
  budgets add that startup overhead. Stopping a service is now its own tool,
  `cancel`, titled "Cancel a job or stop a service", so a host no longer asks
  under serve's "Start a service on a site". `site_clean` removes relay's
  deployment from a site over MCP: destructive, it asks the person on every call
  and keeps the Spack store, as `clio-relay site clean` does. The `use-relay`
  skill teaches the read tools (`exec_read`, `files_read`, `describe` with
  `packages=true` or `job=`), which never ask, and how to stop a service and
  clean a site without the command line.
- `clio-relay` (1.6.26) runs relay 2fac2a09 and bundles clio-jarvis 8104f13a:
  xcompact3d 0.3.4 (archive sha256 a8eb4452?) and pvserver 0.3.4 (18443926?).
  xcompact3d now fails with "xcompact3d diverged: ?" and points at its
  `clio-run-result.json`; pvserver fails with "pvserver did not start: <code>:
  <message>". Both reach CLIO as the failed operation's message, not a bare exit
  code; a failed package service keeps that cause after the connector's reason.
- `clio-relay` (1.6.25) runs relay ff5d63fc with jarvis-cd 7bd046ab. A multi-node
  MPI launch whose graph has no net section, misses launch hosts, or predates UCX
  verification now collects the net facts inside the allocation, saves them, and
  then applies btl, oob and UCX. Relay passes the new shapes through untouched: the
  advisory `net_not_collected` with `site_facts.net_plan`, the launch refusals
  `resource_graph_collect_failed`, `_partial` and `resource_graph_net_invalid`
  as typed issues on the failed operation, and a `launch_collected` question that
  the next check asks before submit.
- `clio-relay` (1.6.24) runs relay 31b5db33 with jarvis-cd ad924e1f. JARVIS sets
  `UCX_NET_DEVICES` only when the node's own `ucx_info -d` lists the device as
  usable; otherwise it raises the advisory `ucx_device_unusable` with per-host
  evidence, and on older graphs it withholds the device (`device_unverified`,
  cause `unverified_graph`). Relay passes both through untouched.
- `clio-relay` (1.6.23) bundles clio-jarvis 53cec00e. pvserver 0.3.3 launches
  its multi-node ranks through the jarvis-cd MPI executor (MpiExecInfo and Exec);
  its archive SHA-256 is 29c0672587fbb5c400c3b66646eee09db535c215524d271dcea6afefdda3f4d0.
  The xcompact3d 0.3.3 files are unchanged.
- `clio-relay` (1.6.22) runs relay da1dbe95 with jarvis-cd 742d7a4a. On a guarded
  site, `exec` runs `facts.jarvis.read` followed by `sched info +json`, `rg facts
  show +json`, `rg skill list +json` or `rg skill show NAME +json` with no shell and
  no plan; answers, installs and submits still ask. The pipelines relay writes name
  no scheduler, so JARVIS detects it. JARVIS's `device_unverified` advisory (UCX
  devices withheld on hosts the graph never saw) reaches `result.site_facts`
  untouched. The `use-relay` skill says how to read site facts.
- `clio-relay` (1.6.21) runs relay 0e52f6a0 with jarvis-cd f6cb7587. Relay turns
  JARVIS's typed Spack failures (exit 6: `compiler_unavailable`, `fetch_failed`,
  `build_failed`, `concretize_failed`, `install_failed`) into typed errors with
  JARVIS's kind and issues, or into the install question when the issue has
  candidates. A blocking `site_fact_uncertain` comes back as `input_missing` with
  JARVIS's issues untouched; an advisory one lets the run go ahead and reaches
  `result.site_facts`. Install asks come only from the current check, so a resumed
  run no longer repeats answered ones. The `scheduler_block` wording names no
  scheduler.
- `clio-relay` (1.6.20): the `use-relay` skill handles JARVIS's `site_fact_uncertain`
  issues (jarvis-cd 16435cda, `docs/site-facts.md`). JARVIS picks deterministically
  and asks only when unsure. CLIO investigates with the issue's own read-only
  probes through `exec` (light ones on the login node, a JARVIS smoke job for
  anything heavier), proposes a value with its evidence and `consequence_if_wrong`,
  and records it with `rg facts answer --set_by <person> --proposed_by <agent>`
  once the person confirms. Then it runs again. Advisory issues are mentioned
  but do not hold the run.
- `spack` (1.0.3): pins clio-kit's spack server to `ef42fcf3`, which removes
  `spack_prepare_site` (five user tools, contract `clio-kit-spack-user-v3`, server
  3.0.0) and points a missing clone (exit 127) to `jarvis spack prepare` through relay.
- `spack` (1.0.2): JARVIS owns deployment, so the `spack` skill prepares a site's
  Spack with `jarvis spack prepare` (jarvis-cd 97c78adb), run through relay `exec`
  as `facts.jarvis.exec` plus `spack prepare --root <facts.jarvis.spack_root>
  --site_spack <root> +json`, with a `plan` on a guarded site. It reads the
  `jarvis.spack-site-prep.v1` record, takes `ambiguous_compiler` (exit 3) to the
  person and reports refusals (exit 5). It no longer calls clio-kit's
  `spack_prepare_site`, and `JARVIS_SPACK_CONFIG` is gone: relay exports
  `JARVIS_SPACK_ROOT`. `spack_site_query` still does the read-only research.
- `paraview` (1.0.1): when a job's live view could not attach while it ran, the
  `paraview-scenes` skill has the agent offer once, when the job ends, to open its
  finished output in ParaView, and open it at the last step once the person accepts.
- `paraview` (1.0.2): the `paraview-scenes` skill says how to join a `pvserver`
  a job serves: one `set_connector_value` with `pvserver` (the forwarded
  endpoint the job's result names) and `version`, with no `address`, then
  `open_view` the job's output by its cluster path. It names the first-attach
  waits and typed failures (`client_fetching`, `paraview_version_mismatch`,
  `node_folder_unwritable`) so the agent stops retrying a failure that repeats.
- `paraview` (1.0.3): the `paraview-scenes` skill names `measure_over_time`, the
  exact statistics of one field at every time step, for a quantity across all of
  a run's snapshots. On a source still being written it measures the steps
  written so far, so the agent can follow a quantity live while the run goes.
  It also names `watch_steps`, which reports each new step of a source still
  being written as task status (or progress when called directly), so the agent
  can follow a run step by step: started as a background task when the run
  begins, it ends by itself with the run (`complete`, `finished`, `not_growing`,
  `stalled` or `cancelled`), and `max_seconds` is given only when the person
  asks for a time limit. Setting up a machine reports each step as progress, so
  the agent waits for it, and `setup_stalled` (a step that fell silent) is told
  to the person.
- `paraview` (1.0.4): the `paraview-scenes` skill says the view's default colour
  range is the 2nd to 98th percentile of the shown values (clio-kit 95d50d06), and
  how to set the range from `measure_field` with `RescaleTransferFunction` when a
  feature still reads faint, symmetric for a signed field on a diverging map.
- `clio-relay` (next release): the `use-relay` skill's "Ask for enough time"
  sizes a job's request as the measured startup overhead plus steps x seconds
  per step plus writes, times a safety coefficient of 1.5 at least (2 on one
  short pilot or none). It overallocates because unused time is not charged
  when a job ends cleanly, says so in the spend approval, and offers another
  partition, a shorter run or more nodes when the padded request exceeds the
  partition's time limit.

## [0.8.0] - 2026-11-13

The stable release of 0.8.0-beta.1, for CLIO 0.9.7, with these changes since the beta.

### Added

- `literature` (1.0.0): searches scholarly sources with CLIO's built-in
  `literature_search` and `literature_lookup` (OpenAlex, Crossref, arXiv, Europe PMC,
  OSTI.gov and DataCite), with a `literature-search` skill. The standard agent (1.2.0)
  includes it (#133).
- `deep-research`: researchers and the critic also search the scholarly literature, and
  the report writes full references for the papers it cites (#133).

### Changed

- `clio-relay` (1.6.19) runs relay integration cbd3cecf with jarvis-cd 97c78adb.
  Install decisions keep their answers across MPI rebuilds and on older sites,
  each install round has its own JARVIS execution, and the site's network comes
  from the resource graph that JARVIS collects in a job and applies to every MPI
  launch.
- `clio-relay` (1.6.18) runs relay integration caee019f with jarvis-cd bfeff98b and
  bundles clio-jarvis dc5270e2 (xcompact3d 0.3.3, pvserver 0.3.2). Relay is the
  middle man: JARVIS owns the site's network, queue moves, install decisions,
  pipeline checks and Spack preparation, and relay turns JARVIS's questions into
  asks for the person. A serve forwards the port the service bound, as JARVIS
  reports it, and its task completes when the service is ready. A package
  parameter that wraps an input's name in a placeholder is refused. The use-relay
  skill sends the agent to the site's resource graph, JARVIS's scheduler report
  and site skills, and to JARVIS's typed issues, and names no cluster, scheduler
  or MPI of its own.
- `clio-relay` (1.6.17) runs relay integration 21fffaa5 and bundles clio-jarvis
  82debc68 (xcompact3d 0.3.2, with case-scoped parameter checks and sizing
  guidance). When a job waits far off in a busy partition and another has idle
  nodes that fit, relay asks the person to keep waiting or move it, and moves the
  pending job in place. The agent leaves the queue unset unless the person names
  one, so the site's default applies. A coupled pipeline marks only its serving
  step as the service. `site clean` ends operations whose jobs were cancelled
  outside relay and cancels those still waiting on the person. The use-relay skill
  shows the coupled pipeline and says to pass relay's queue question on as it is.
- `clio-relay` (1.6.16) runs relay integration b5c98e2c. A site's MPI choice
  carries to the next install on that site until the person declines it. A serve
  with `path: auto` takes ssh when frp has no client or token. A queued job shows
  Slurm's start estimate and the partitions with free nodes. Multi-node runs name
  the network Open MPI's TCP channels use, found from Slurm's node addresses and
  kept per site, and a run that fails on the wrong interface carries
  `mpi_network_hint` naming that record. The use-relay skill says how to act on
  each: offer another partition, keep the carried MPI, and write the nodes'
  fabric to the record before running again.
- `clio-relay` (1.6.15) runs relay integration d87eeb55, and `spack` (1.0.1) runs
  clio-kit edf67da2. A package's install job takes one whole node and Spack builds
  with all its CPUs. `spack_prepare_site` prefers compilers with Fortran, the site
  MPI's first, so Spack 0.23 concretizes the stack to the compiler the site's
  upstream was built with and reuses it. jarvis-cd af290aef offers the site MPI's
  real install, not its external alias. Relay's tools declare a closed world, so a
  plan approved for auto-execute runs them without a permission prompt while
  relay's own asks still reach the person. A failed install carries its log and
  job, and the use-relay skill says to yield on a long task, read that log, and
  prepare Spack again with `compiler=` when a compiler check fails.
- `clio-relay` (1.6.14) runs relay integration bdd1541b: a package archive's
  SHA-256 no longer depends on the Python relay runs under. CPython 3.14 on Windows
  links zlib-ng, so the same files had given xcompact3d 9763fc95 there and
  0089efeb elsewhere. Archives are now stored-block gzip: xcompact3d 6f30a7a0 and
  pvserver 6736500f everywhere, and a guarded site asks the new review once.
- `clio-relay` (1.6.13) runs relay integration 43ff03ed and requires the `spack`
  plugin. When a site has no Spack for JARVIS, relay's `missing: spack` refusal
  carries a `remedy` (`prepare_spack`: the CLIO Spack root and config, and the
  site's own Spack with why relay does not build into it). The use-relay skill maps
  it to `spack_prepare_site` and the same `run` again. Package archives no longer
  depend on the checkout (line endings, exec bits), so the bundled clio-jarvis
  stages xcompact3d 0089efeb and pvserver dcb18420 on every host; a guarded site
  asks the new review once.
- `clio-relay` (1.6.12) runs relay integration cb4c790b: after a plugin update, a
  package name follows the bundled clio-jarvis. A run, stage, list or describe by
  name stages the archive the current copy builds, marks the older one
  `superseded_by`, and a guarded site asks the new archive's review. Pinning an
  older `sha256` still runs it.
- `clio-relay` (1.6.11) runs relay integration 3f25846a, which pins jarvis-cd
  c95fa922: cancelling a running job works on a Slurm without accounting. A site
  with relay's older jarvis-cd gets the reinstall ask on its next package run.
- `clio-relay` (1.6.10) runs relay integration 40f4f634: a clean site runs end to
  end. Relay finds a Python 3.11 or newer for jarvis-cd itself (`python3`, then
  `python3.N`, then the site's python modules), or uses the site's `jarvis_python`
  setting, and package jobs use that same Python. The install job gets its own
  walltime (`install_walltime_s`, 4 hours by default) instead of the run's. The
  plugin's clio-jarvis copy adds `pyproject.toml` and `spack/` from aa8b3d56, so the
  package archive carries its Python requirements and Spack repository; its SHA-256
  changes, so the first stage asks for a new review. `site clean` really removes
  relay's deployment, and a cancel withdraws the run's pending asks.
- `clio-relay` (1.6.9) runs relay integration 84c2bb77: the plugin ships clio-jarvis at
  aa8b3d56 in `packages/` and hands it to relay as `CLIO_RELAY_PACKAGE_SOURCES`, so
  staging a clio-jarvis package runs no git and needs no account. A person's own packages
  reach a site through relay's file transfer. The `github` account and its grant file
  are gone. Relay on Windows also loads psij without `SIGCHLD`, takes a job duration in
  seconds, holds an ssh forward to a compute node through the login node under CLIO's
  fence, and names an antivirus block of `frpc`.
- `clio-relay` runs relay integration 0144fb2e: package staging works under a sandbox
  that denies renames in its temp folder (git checkouts live under relay's state), and a
  private GitHub source is fetched with the person's GitHub account: the plugin declares a
  `github` account and hands relay its grant file.
- `clio-relay` runs relay integration 93f3fe92: relay's scratch dirs inherit their parent's ACL
  on Windows, so a relay in an AppContainer can use them (Python 3.13+ `mkdtemp` cannot).
- `clio-relay` runs relay integration 66451813: relay finds `ssh`, `scp`, `frpc`, `ssh-keygen`
  and `git` on the PATH with PATHEXT, so a host's `ssh.cmd` shim wins on Windows.
- `clio-relay` runs relay integration bbda1d29: each serve endpoint port has an `address`,
  `host:port`, so a host that rewrites addresses can publish tcp ports too.
- `clio-relay` runs relay integration 93a11e4f: a `packages` tool stages JARVIS packages
  (git at a commit, by default relay's pinned clio-jarvis, or a directory on the relay host),
  lists and removes them; the use-relay skill says when to stage.
- `clio-relay` runs relay integration d3a1a360: catalog endpoints take the Security default (Secure), and the sign-in copy reads "Needs an ssh sign-in".
- `clio-relay` runs relay integration d1f3f5c2: `site clean`, `shutdown` (it reports
  processes it can't confirm) with an authenticated HTTP stop, the worker's `link_mode` (`brokered_tcp` or
  `udp_rendezvous`), relay's pinned jarvis and the `ambiguous_provider` choice.
- `web` (2.0.0) uses CLIO's built-in `web_search` and `web_fetch` instead of clio-kit's
  Web Search MCP server (its `mcp.json` is removed), with a new `web-research` skill
  (#133).
- `deep_researcher` (0.4.0): a claim still unsupported after the repair is dropped with a
  note instead of stopping the run, and the corrected report is delivered with the
  reviewer's open notes (#133).

### Fixed

- `pdf`: the `create-pdf-report` skill writes the PDF where the person asked, under the
  name they gave, and keeps intermediate renders out of the project (#131). When a page
  was not shown to the model, it names the page instead of claiming visual
  verification (#132).
- `deep-research` no longer stalls deriving claim and gap IDs, and binds the critic's
  evidence from inline fetches (#133).

## [0.8.0-beta.1] - 2026-11-11

### Added

- `ndp` agent (1.0.0): the standard agent plus the `ndp` plugin, for National Data
  Platform work.
- `geodesy` (1.1.0): `station_catalog.py within` lists a normalized catalog's stations
  within a great-circle radius (nearest first, with input rows and invalid skips), so
  the region and coverage skills work when the geo MCP server is not running.
- `wtfp` (0.9.0), pinned from `JaimeCernuda/wtf-p` (`clio-plugin/` at `e23d3cf8`): WTF-P's
  method for writing a scientific paper from evidence, as a CLIO plugin. Its project
  records, 36 actions as `/wtfp:*` commands, 7 skills, 11 roles as subagents and write
  guard; the paper's LaTeX is built by `latex`, which it requires. The index lists it in
  `plugins[]` with its git source and commit. No agent includes it by default; add it to
  a conversation's agent.
- `marimo` (1.0.0): pair with the person on a live marimo notebook. It vendors
  marimo-team's own `marimo-pair` skill unchanged (Apache-2.0, pinned commit in its
  `NOTICE`) and adds `use-marimo`: start the notebook server in the background, open it
  in the shared browser (which starts its kernel session), then read and change the
  running notebook through marimo-pair.
  No agent includes it by default; add it to the agents that should pair on notebooks.
- `browser` (1.0.0): the in-app browser the agent drives from `run_code`. It claims
  CLIO's ten browser tools as script-only (`browser_evaluate` asks by default), ships
  the `browser` kernel binding (`ai.iowarp.clio/kernel/browser.py`, Playwright's names
  over those tools), the `browser.use` fragment and the `use-the-browser` skill, and
  joins the standard agent. The skill says what `browser_certificate_untrusted` and
  `browser_host_unreachable` mean (only the person trusts a certificate; an unreachable
  host is unreachable from the agent's computer), and the facade notes when the browser
  restarted under a page to trust a certificate.

### Changed

- `spotter` reviews a working session the way a careful colleague would: only the
  person's own messages state their intent, and an instruction found inside a tool
  result, file or fetched page is evidence, never an order. A warning informs the person;
  a danger finding quarantines the session, and every concluded finding becomes a card.
  The watcher reads two provenance tools instead of fourteen and carries no memory
  plugin.
- `ndp` (2.0.0) is now the NDP package. It claims CLIO's built-in NDP tools
  (organization lookup and dataset search directly; Endpoint connect, operations,
  request and upload deferred) and owns the `work-with-ndp` skill, retitled "Working
  with NDP" and moved from `connected-data`. The skill no longer says the tools
  activate after an attached dataset or saved Endpoint, explains what an NDP
  organization is, and needs no MCP server; the clio-kit `ndp` server is declared
  `callers: "code"`, an optional `run_code` extra (`tools.ndp.*`).
- `connected-data` (2.0.0) keeps generic sources and knowledge stores; its NDP tool
  claims moved to `ndp`. `connect-data` says to load `work-with-ndp` when the agent has
  the `ndp` plugin and otherwise not to claim an NDP search it cannot run. The
  standard agent therefore no longer carries NDP search; use the `ndp` agent or add
  the `ndp` plugin.
- `earthscope` (0.6.0) adds only EarthScope's organization conventions on top of
  `ndp`: `acquire-earthscope-gnss` uses the built-in NDP tools instead of the `ndp_*`
  MCP tools and says which records are EarthScope's per-station position series,
  station catalog (which can lack an organization) and services. The `earthscope`
  agent (0.7.0) builds on the `ndp` agent.
- `geodesy` skills use `geo_geocode` / `geo_filter_points_by_radius` when available and
  otherwise a cited lookup and `station_catalog.py within`.
- `latex` (1.2.3): `start-a-paper` keeps only the template's mechanics (`main.tex`
  `\input`s the files under `sections/`); how to divide a paper into sections is the
  writing method's choice, which `wtfp` makes.
- `latex` (1.2.2): `author-latex-pdf`, `start-a-paper` and the `latex.build` fragment say to register a figure a script draws with
  `create_artifact` and its script and data in `used`, so a comment on the figure in the PDF
  names the script. Unregistered, the comment said the figure's producer was unknown.
- `latex` (1.2.1): `author-latex-pdf` covers checking whether a paper is ready for a venue
  (page limit, double-blind review, required packages, paper size), and the `latex.build`
  fragment says page counts and venue checks are measured on the built PDF, not read from
  the source. Asked whether a paper was ready for a venue, the agent had answered from the
  source without building.
- `latex` (1.2.0): a build makes the paper, one artifact shown by its title and built from
  the versions of the source files it read. Each `template.yaml` names the paper's
  `document_type` and its `venue`, which the paper's card shows ("Paper", "IEEE
  conference"). `author-latex-pdf`, `start-a-paper` and the `latex.build` fragment say
  that the paper is the deliverable, set `\title` early, and leave the PDF's path out.
- `latex` (1.1.0): builds go through CLIO's `latex_build` tool, which CLIO implements
  with the pinned Tectonic 0.17.0. The tool reports every problem by file and line, and
  with a venue it also checks the paper against that template's rules.
  `author-latex-pdf` is rewritten around the tool, and its `scripts/render_latex.py`, a
  second Tectonic call, is deleted. The plugin now ships `templates/`:
  `ieee-conference`, `ieee-journal`, `acm-sigconf` (review, anonymous), `acm-journal`,
  `springer-lncs` and `elsevier`. Each has a `template.yaml` with its class, options
  and venue rules (page limit, references, double-blind, packages, paper size), and a
  starting project that builds with its citation resolved. The new `start-a-paper`
  skill says how to begin from a template, and the `latex.build` fragment says the
  templates and venue checks exist. `latex_outline` (sections, figures, tables and
  equations with their source lines and PDF pages) and `latex_locate` (a PDF point to
  its source line and back) are declared too.
- `document-production` (0.2.2): the anchor reference reads the Source, Figure and
  Graphics lines of a mark on a LaTeX paper's PDF.
- `document-production` (0.2.1): `review-document-artifact` and its anchor reference
  read the comment entries CLIO now sends: a header naming the version and what to
  edit, a labelled overview and crops, and one entry per mark (S1, S2, ...) with its
  Selected, Under, Source, Picture and Made by lines. The answer is stored as the reply
  on each comment, so it goes by label.
- `visuals` (1.2.2): `review-visual-presentation` says how to act on a figure comment:
  change the producing script, rerun it, look at the new image with `view_image`.
- `pptx` and `xlsx` (1.0.1): their editing skills find a comment's slide shape or cells
  from the entry's Source line, since comments no longer carry raw anchor profiles.
- Delegation roles use shorter prompts, and skills carry one-sentence trigger
  descriptions. Exploration locates files before reading them. `run-a-study` runs a
  small study in the conversation, and a study's view is a dashboard.
  `create-dashboard` reads the latest version of file and stream sources and
  registers a new file version after each rewrite. The browser skill reports a
  refused page instead of allowing it.

### Fixed

- `hdf5`: the SWMR guide shows the whole-file and one-dataset forms of
  `h5format_convert -d` (it does not downgrade a file) and its writer example imports
  `time`. The chunking guide no longer names a removed skill, parallel HDF5 readers
  no longer set early allocation themselves, and the map-objects guide is removed
  because only the DAOS VOL can hold maps.

## [0.7.0] - 2026-10-28

The marketplace is rebuilt around `ARCHITECTURE.md`: each kept agent ships its
own plugin whose `mission` fragment says whom it serves and what it does; L1
method plugins hold no program; programs, formats and sources are separate L2
plugins; every plugin with domain content carries the skill-literal lint.

### Added

- `clio-data` (CLIO Data): inspects, checks and converts HDF5/netCDF-4, ADIOS2
  BP4/BP5 and Parquet files, with a verified conversion script
  (`convert_to_parquet.py`: written, read back, rows, nulls, NaNs and
  per-column checksums compared). It replaces `data-semantics` and
  `format-bridge`.
- Plugins `adios` (clio-kit's adios server plus an `adios2` skill),
  `data-onboarding` (L0, shared by clio-data and OPAL), `phenotyping` (L1),
  `geodesy` (L1, with `fit_trajectory.py` and `station_catalog.py`),
  `fea-methods` (L1), and the program plugins `morphorm` and `slurm`, which
  carry DaisyQuach's factorio-flat 0.5.0 work: the Morphorm workflow, its
  restart and bundled checks (`exo_summary.py`, `xml_params.py`,
  `diag_summary.py`), `hpc-batch-jobs` with `wait_job.sh`, and their tests.
- `parquet` gains its `parquet` skill; the `hdf5` skill carries the tool
  guidance; `scientific-method` gains `run-non-interactive-task`.

### Removed

- The blueprint-era demo agents `genomics-review`, `geospatial-field-review`,
  `hpc-io-regression`, `materials-crystal-review`, `ndp-environmental-hazards`,
  `proteomics-mzml-review`, `remote-sensing-ogc-review`,
  `seismic-waveform-review`, `terrain-suitability` and
  `wildfire-smoke-impact-review` (with the `wildfire` plugin and its
  smoke_review flow), with their plugins.
- `phenotype`, the synthetic workload that APPL-CORE (OPAL) replaces, with its
  plugin and the `phenotype-impl` CI job.
- `data-semantics` and `format-bridge` (folded into `clio-data`),
  `documents-review` (folded into `document-production`), `topology` (split
  into `fea-methods` and the `abaqus` and `morphorm` programs), and the
  leftover Codex `agents/openai.yaml` files.
- The smoke-test agents `hook-smoke` and `mcp-calculator-smoke` and their
  plugins leave the default marketplace, so people choosing an agent see only
  agents meant for work. They live in `testing/`, a separate marketplace named
  `clio-testing` that CLIO's own checks install; CI checks it alongside the
  default one.
- The blueprint-era topology experiments, superseded by the flat agents that
  load procedures on demand: the Factorio principal-investigator agent and the
  EarthScope GNSS region agents (`earthscope-gnss-region`, `earthscope-flat`
  and the archived depth and width topology variants), with the plugins only
  they used (`earthscope`, `earthscope-flat`, `earthscope-gnss`,
  `earthscope-gnss-region-depth`, `earthscope-gnss-region-width`).
- `base-agent` (now the `standard` agent), `cluster-operator` (retired relay
  reference with no tools left to provide) and wildfire's declared `workflow:`
  block, now the `smoke-review` flow, which runs the stages on the core
  `workflow` flow.

### Changed

- deep-researcher 0.3.0 runs deep research as the `deep-research` flow,
  shipped in its plugin (0.3.0) and started with `run_flow` (the agent adds
  `orchestration`). The flow plans directions (a recorded model step that
  chooses how many, up to `max_directions`, default 6), researches them in
  parallel (`concurrency`), has the critic verify them, researches the gaps the
  critic names for at most `max_rounds` (default 2) more rounds, and writes the
  report (a recorded model step) from verified claims only, appending the
  unresolved questions and rejected claims; the report is written to the
  workspace and its typed fields ride the result's `workflow_state`.
  `researcher_model` and `critic_model` choose each subagent's model. The
  critic returns a typed audit in `workflow_state.audit` (verified claims with
  fetched source and quote, rejected claims with reasons, gaps), which the flow
  validates. The coordinator answers simple questions directly and delivers the
  flow's report with `create_artifact`; its fragments are gated on `run_flow`
  so the subagents never read them. The `rounds`, `sources` and `verification`
  fragments and the `deep-research-report` skill are removed: the flow and the
  writer's instructions now hold that method.
- Factorio 0.6.0: its identity no longer repeats its name; `factorio.mission`
  says whom it serves, that no simulation program is the default, and that it
  runs meshes, solves and batch jobs itself when it can; a roster fragment
  makes consulting a specialist an ordinary tool call. Every Factorio subagent
  can read files, and those that compute or build can write and run them;
  each declares the plugins its skills reference.
- `manufacturing` is an L1 method pack with no program: `materials`,
  `manufacturing-processes` (was `am-process`), `characterization`,
  `mechanical-testing`, `fatigue` and `fea-methods`. `abaqus` is the Abaqus
  program plugin with Tosca, the topology views, the `abaqus-topology` catalog
  (instance values scrubbed) and `abaqus_engineer`.
- Skill merges: inconel-718 removed; pbf-lb → am-process-parameters;
  surface-finishing → post-processing; microstructure-characterization →
  microstructure; porosity-analysis → xct; fatigue-testing →
  mechanical-testing; mts-test-systems → load-frame-capability;
  scientific-plotting → data-visualization; research-methodology →
  experimental-design; formulate-abaqus-package → abaqus.
- `scientific-method` is part of the CLIO Science base, with domain-neutral
  examples; Factorio's own process skills moved into `factorio`.
- EarthScope 0.6.0: `earthscope-skills` is renamed `earthscope` (an L2 source
  plugin with a mission and discovery-based acquisition, no hardcoded resource
  literals); GNSS methods live in `geodesy`; `pandas` and `plot` are dropped.
- APPL-CORE 0.3.0 is shown as "OPAL": split into `data-onboarding`,
  `phenotyping` and `appl-core`; the export contract is version 6 and other
  versions are refused; inputs are described by convention, not as read-only;
  the `appl-instruments` placeholder is removed and `geometry-to-glb` moved to
  `visuals`.
- SPOTTER (`spotter-ai` 0.5.0) watches any CLIO session: the eight phenotype
  campaign tools are gone; alerts go through `raise_alert_card` and
  containment through CLIO's SPOTTER clearance; one mission fragment, with the
  skills investigate-provenance, inspect-attention and contain-anomaly.
- deep-researcher 0.2.0 has web only in its researcher and critic subagents and
  a mission-first coordinator prompt; document-production 0.2.0 and
  clio-search 0.2.0 lead with a mission that describes their actual tools.
- The `workspace` plugin (1.1.0) carries CLIO's read-only repository inspection
  tools `fs_list_directory` and `fs_search_text` in place of `fs_glob` and
  `fs_grep`, matching CLIO's file server.
- The `visuals` plugin's diagram guidance points at the active catalog's
  `clio.mermaid.v1` entry for families, syntax and viewer capabilities, as
  0.6.13 did for the blueprint agents; `create-diagram` covers choice and review.
- HDF5 guidance lives in the `hdf5` plugin (1.1.0) as one `hdf5` skill by the
  HDF5 team: a router plus 22 guides under `references/`, audited against HDF5
  2.0–2.2 and h5py 3.12–3.16 (from iowarp/clio-agent#1736, which proposed it
  as a CLIO built-in). Every agent that adds `hdf5` gets it. `data-semantics`
  (0.2.0) drops its 21 older `hdf5-*` skills, and its HDF5 subagent loads the
  new guides, `references/clio_core_ingest.md` for clio-core ingest.
- The marketplace moves from Agent Blueprints (`AGENT.md` plus `experts/*.md`)
  to native Agent Plugins 1.0.0 packages under `plugins/` and Python agent
  classes under `agents/`. Every agent keeps its id; experts become defined
  subagents of the plugin they belong to, root prompts become domain
  fragments, and skills move to hyphenated folders in the plugin that owns
  them. Shared capabilities (workspace, shell, web, documents, visuals,
  delegation, connected data, the clio-kit servers) are single plugins the
  agents depend on, so `create-pdf-report` and the document skills have one
  home.
- The spotter and phenotype MCP projects move to `plugins/<id>/impl` and
  launch from `${PLUGIN_ROOT}`. The archived `old/` agents are converted too;
  tools no MCP server in the repository provides are not carried. hook-smoke's
  `pre_message` is an SDK `prompt_submit` hook.
- CI runs `clio-agent plugin check .`; the policy scripts check the plugin
  layout instead of `AGENT.md`.

### Renamed

- `factorio-flat` is now `factorio` (agent and plugin, 0.5.0): the flat
  research partner replaces the earlier Factorio agent under its name.
- `earthscope-single-agent` is now `earthscope` (0.5.0): one agent loading the
  `earthscope-skills` procedures on demand. Refs to the old ids no longer
  resolve; use `clio/factorio` and `clio/earthscope`.

## [0.6.13] - 2026-10-21

### Changed

- Shared task guidance distinguishes waiting, consultation, pause and cancellation
  while retaining the assignment and returned evidence.
- Base Agent 0.2.9, APPL-CORE 0.2.6, Factorio Flat 0.4.4 and EarthScope 0.4.4
  discover diagram families through the active catalog and use read-only repository
  inspection. These pack versions require CLIO 0.9.5b8 or later.

## [0.6.12] - 2026-10-18

### Added

- CLIO Search offers bounded read-only session and file-passage search.
- Standard agents discover diagram, HTML/SVG and visual-review capabilities
  without prescribing a particular layout or requiring a diagram for every task.

### Changed

- Base Agent 0.2.8, APPL-CORE 0.2.5, Factorio Flat 0.4.3 and EarthScope 0.4.3
  share content-driven composition and captured-image review guidance.
- Shared task guidance explains accepted work, consultation and cancellation.
- APPL-CORE verifies onboarding before claiming it is ready to analyze a dataset.
- APPL-CORE presents evidence in natural prose with specific clickable references.
  Bracketed claim tags are no longer required or rewarded by the grader. Status
  commands and pending audits cannot substantiate scientific findings.
- APPL-CORE 0.2.4 investigates messy read-only source data with adaptable queries
  and code. Cards, loaders, repeat execution and the five bundled view schemas
  are optional aids. Missing or unfamiliar export versions trigger inspection
  instead of blanket refusal. Acceptance cases now require source preservation
  and grounded findings/adaptations rather than a prescribed script pipeline.
- Shared Data Semantics inspection and quality guidance preserves source data
  and distinguishes uncertain meaning from computational obstacles.

### Added

- Base Agent, APPL-CORE, Factorio Flat and EarthScope declare the shared managed
  execution/document tools. Discovery is optional for standalone paths/import
  checks; document work requests converter/font preparation separately. Pack
  versions advance and require CLIO beta 3 or later for these native tools.
- Opt-in skill literal checks reject dataset-specific facts in reusable pack prompts.
  Packs can supply a denylist, enable generic checks, and mark deliberate examples.

## [0.6.11] - 2026-10-05

### Added

- SPOTTER reads configured Flowcept attention captures with CLIO's shared profile
  reducer and attaches capture references and uncertainty to reviewed findings.
  Partial, ambiguous, mismatched and out-of-root captures produce explicit errors.

### Changed

- APPL-CORE keeps generated cards, loaders, audits and views in the owning
  workspace's Agent state, using the canonical directory supplied by CLIO.
- Marketplace qualification uses Python 3.13, matching CLIO's managed runtimes.
- APPL-CORE and SPOTTER require CLIO 0.9.5b3 for their workspace-state and
  attention handoffs; older runtimes hold the packs with an explicit version error.

The beta-3 integration has source and recorded-capture validation. Fresh Delta
inference and both OPAL demonstrations remain separate live acceptance work.

## [0.6.10] - 2026-10-02

### Added

- Base Agent (0.2.4) can fetch web pages and files with `web_fetch` (the
  clio-kit web MCP server, declared the same way Deep Researcher declares it)
  and can pause to ask the user a question with the native `ask_user` tool.
  Both work on runtimes that already run this pack, so it keeps no
  clio-agent floor.
- APPL-CORE Analyst (`appl-core`, 0.1.0), an analyst for any APPL-CORE
  plant-phenotyping export (an L2 agent: one export format, any experiment,
  no pack changes). On first contact it reads the export's self-description,
  runs bundled audit scripts (`inventory.py`, `audit_columns.py`,
  `join_keys.py`, `flag_check.py`), and records an experiment card, a saved
  loader, validated views, and audit reports in the active workspace under
  `.clio/datasets/<key>/`, where `<key>` comes from the SHA-256 of the
  export's manifest (`card.py --store <workspace_root>`; it also verifies
  loader and view hashes). Keeping these out of the export by default leaves
  the raw data pristine, works with shared data mounts, and lets another
  session or path find the same export again; the pack sets defaults only
  and leaves what may be written to clio's approval modes, deny rules,
  allowed roots, and sandbox. The expert carries Base Agent's
  general-purpose tools (file edits, `view_image`, `view_pdf`, `web_fetch`). Onboarding can run in a child agent (`audit-dataset`); the
  parent re-runs the returned loader before trusting the card. Skills carry a
  level keyword (`level:L0`/`L1`/`L2`); the L1 phenotyping skills are drafts
  with JSON Schemas and a validator for the design, observations, spectra,
  assets, and events views; the L2 skills are placeholders until the
  falsifier experiment decides their content. `geometry-to-glb` converts
  vertices/faces/colours text, PLY, and point clouds into viewport meshes.
  The pack ships `.lint-l3` and `lint-denylist.txt` for the skill-literal
  linter, black-box eval cases with a grader and a held-out variant maker,
  and requires clio-agent 0.9.4.19 or newer (for `clio.mesh-viewport.v1`).
  CI runs its tests in a new `appl-core-pack` job.

- Factorio Flat (0.3.0) can show Abaqus geometry and results interactively.
  The new `abaqus-visualization` skill ships the exporter (`odb_to_glb.py` for
  ODBs, `fea_glb.py` for `.inp` meshes and Tosca STLs) that writes `.glb`
  meshes with node and cell fields over frames, and `render_view.py`, which
  draws report figures from the same files and the camera the scientist
  chose. The new `visualize-topology-optimization` skill and `abaqus-topology`
  pack catalog show a topology run two ways: before and after in two linked
  3D viewports with a von Mises stress toggle on one shared scale, and the
  design history with a density threshold slider, a design-cycle slider, and
  the convergence plot. `TopologyViewport` aliases the `clio.mesh-viewport.v1`
  kernel and `ParameterSlider` the `clio.slider.v1` kernel, a slider with a
  step and a box to type an exact value (both clio-schemas 0.4.0). Factorio Flat
  now requires clio-agent 0.9.4.19 or newer for its pack catalog (raised from
  0.9.4.17: that release reads the `a2ui_catalogs` list form but does not pin
  clio-schemas>=0.4.0, so TopologyViewport/ParameterSlider cannot load).

- The domain agents are now supersets of the standard agent (Base Agent):
  APPL-CORE Analyst (0.2.0), Factorio Flat (0.4.0) and EarthScope Skills
  (0.4.0) each have everything Base Agent has, plus their own domain.
  - Tools: the root expert declares all of Base Agent's tools (`shell_bash`,
    file read and edits, `view_image`, `view_pdf`, `web_fetch`, `ask_user`).
    EarthScope Skills gains all of them and the clio-kit web server;
    Factorio Flat gains file read/edit and `web_fetch`.
  - Skills: each declares clio's built-in `work-with-pdfs`, `planning`,
    `update-models` and `present-interactive-analysis`, which Base Agent gets
    automatically, and ships `create-pdf-report`. Factorio Flat drops its own
    copy of `work-with-pdfs` (identical to clio's) and uses the built-in.
  - A2UI tools come from each agent's declared catalogs, as Base Agent's do,
    instead of a partial explicit list.
  - Prompts: Base Agent's working principles are now a `## Working principles`
    section (stay grounded in inspected content, smallest tool sequence,
    report failures plainly, verify edits, and when to read or write a PDF),
    carried word for word by each domain agent.
  - Base Agent (0.2.5) ships `create-pdf-report`, so writing a PDF on request
    is part of the standard agent.
  - A new test, `tests/test_standard_agent_superset.py`, reads Base Agent as
    the source and fails if a domain agent lacks any of its tools, MCP
    servers, catalogs, skills or principles.
  - APPL-CORE Analyst requires clio-agent 0.9.4.23 or newer, the first release
    whose catalog has the `clio.chart.v1` presets its views use.

### Changed

- `clio.time-series.v1` is removed upstream in favor of one Altair/Vega-Lite
  chart layer (`clio.chart.v1`, clio-schemas 0.5.1); the two packs that used
  it move over (#1533). Factorio Flat's `abaqus-topology` catalog
  re-expresses `ConvergencePlot`'s `xKey`/`yKeys`/`series` as the
  `trajectories` preset's `xField`/`yField`/`entityField` over inline `data`
  (or `dataUri`). EarthScope Skills' `visualize-earthscope-gnss` primary plot
  moves to `clio.chart.v1` with a Vega-Lite `spec` authored through
  `present-interactive-analysis`'s Altair support, folding the confirmed
  `east`/`north`/`up` columns into one line per component (no named preset
  reshapes a wide table that way). Both packs' `requires.clio_agent` floor is
  raised to `>=0.9.4.23`, the first clio-agent release that pins
  clio-schemas>=0.5.1.

## [0.6.5] - 2026-09-24

### Changed

- A2UI catalogs are now declared per agent. clio-agent 0.9.4.17 makes an
  agent's `a2ui_catalogs` the complete list of catalogs it may produce
  against, in preference order, with nothing implicit. Every shipped agent
  lists the builtin `clio-workspace` catalog, so every one keeps A2UI: Base
  Agent (0.2.3), Factorio Flat (0.2.1), SPOTTER AI (0.3.1), Cluster Operator
  (0.1.1), Data Semantics (0.1.1), Deep Researcher
  (0.1.1), Document Production (0.1.1), EarthScope Flat
  (0.1.1), EarthScope (0.1.1), Factorio
  (0.1.1), Phenotype (0.1.1), and NIFC (0.1.1).
  EarthScope Skills (0.3.1) lists `clio-workspace` first, as the default for
  tables, charts, and metrics, then its own `earthscope-stations` catalog.
  A station view names its catalog; clio-agent's generated catalog skill
  states the catalogId. No shipped pack lists the builtin Basic catalog.
- EarthScope Skills uses the list form of `a2ui_catalogs`
  (`- earthscope-stations: catalogs/earthscope-stations`). Its README
  describes the per-agent rule for pack authors.
- EarthScope Skills now requires clio-agent 0.9.4.17 or newer, the first
  release that reads the list form; an older runtime would drop its station
  catalog. The other packs list only builtins, which an older runtime still
  offers, so their floors are unchanged.

## [0.6.4] - 2026-09-23

### Added

- Base Agent (0.2.2) declares `view_image` and `view_pdf`, so the PDF workflow
  CLIO gives it can inspect rendered pages of drawings and scans, and read a
  PDF natively on a PDF-capable model.
- Factorio Flat declares `view_pdf`, and the `work-with-pdfs` skill reads a PDF
  natively with it when the connected model is PDF-capable, falling back to
  the conversion and rendered-page workflow otherwise (requires clio-agent
  0.9.4.15 or newer).
- EarthScope Skills ships its own A2UI catalog (`earthscope-stations`,
  `catalogs/earthscope-stations/`): a `StationMap` (aliasing `clio.map.v1`)
  and a multi-select `StationPicker` (aliasing `ChoicePicker`), alongside the
  Basic `Text`/`Column`/`Row`/`Button` components, delivering a structured
  `earthscope.stations.selected` domain event — no clio-agent or gact-tui
  source change required. See `earthscope-single-agent/README.md`'s "Custom
  A2UI catalogs" section for how a pack author adds one.
- Factorio Flat can prepare existing PDFs as bounded Docling text, structured
  JSON, and rendered page images, including a visual-only path for engineering
  drawings, scans, equations, and other layout-dependent evidence.
- Factorio Flat includes a separate PDF-report creation skill which activates
  only when a scientist explicitly requests a PDF deliverable; ordinary reports
  remain Markdown.

### Changed

- EarthScope Skills' acquisition procedure and root prompt route station
  selection through the new catalog skill (`a2ui-catalog-earthscope-stations`)
  and the `earthscope.stations.selected` event instead of the generic
  `ChoicePicker` + `agent.submit` recipe.

### Fixed

- PDF guidance now uses materialized workspace paths for both `@` references
  and uploaded sources, distinguishes rendered output from actual visual
  inspection, and prohibits guessing dimensions or units from extracted labels.
- SPOTTER AI syncs its environment when its MCP server starts instead of
  running against a possibly stale one.
- EarthScope Skills now requires clio-agent 0.9.4.15 or newer (the first
  release that serves its A2UI catalog) instead of an unreleased 0.9.5.

## [0.6.3] - 2026-09-13

### Added

- Base Agent, a configurable general-purpose blueprint with native workspace
  tools and no hidden routing hierarchy.
- EarthScope Skills, a focused single-agent GNSS workflow with optional regional
  fanout, interactive station selection, analysis, visualization, and reporting.
- Factorio Flat, a small-model-friendly scientific research blueprint with
  bounded evidence fanout, review, virtual-lab, and Abaqus handoff skills.
- Daisy Quach's Factorio Flat materials-science expansion, adding specialists
  for materials, manufacturing, characterization, mechanical testing,
  fatigue and failure, and scientific data analysis alongside the original
  research and simulation experts.
- A standalone phenotype workload package and provider-aware SPOTTER AI
  provenance services for native, Flowcept, CMF, and JSONL stores.

### Changed

- Deep Researcher uses committed child waits, explicit artifact source records,
  and standardized citations.
- EarthScope blueprints inherit the session model, preserve user station choice,
  use reviewed installed MCP launchers, and prefer interactive scientific views.
- Cluster Operator uses the relay's held-channel artifact list and read tools and
  aligns its expert signature with the runtime's populated question field.
- Marketplace policy now validates model pins, parsed blueprint contracts,
  native orchestration prompts, and behavioral Factorio outcomes.

### Fixed

- EarthScope single-agent acquisition stages a selected station directly from
  verified catalog evidence rather than reapplying an earlier discovery radius.
- Factorio Flat rejects contradictory traces, empty completed-child results, and
  ungrounded completion claims.
- SPOTTER retains anomaly acknowledgements and removes environment-pinned model
  selection so the active session provider remains authoritative.
