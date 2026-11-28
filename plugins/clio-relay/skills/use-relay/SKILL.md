---
name: use-relay
title: Using relay's compute sites
description: Use this skill to run jobs, commands, file transfers or services on the person's compute sites through relay. It says how to find the sites and how to get each site's own guide.
---

# Using relay's compute sites

Relay reaches the compute sites the person has set up, such as a cluster over
SSH, a Globus Compute endpoint or a Tapis tenant. Its five verbs are
`describe`, `run`, `exec`, `files` and `serve`. Beside them, `packages` adds
a JARVIS repository the person wrote to a site's JARVIS root, `install`
installs a package's software on a site ahead of any run, and `shutdown` stops
relay's long-lived processes when the host closes.

## Relay is the way to a site

Relay owns the connection to every site the person has set up, whatever its
transport, and it keeps the person's guard, their asks and the record of what
ran. An `ssh`, `scp`, `rsync` or scheduler command (`sbatch`, `squeue`,
`qsub`) from a shell tool reaches the site without any of those. A site's
transport and config are how relay reaches it: `describe(site=...)` reaches
the site and, when relay cannot, says why with a typed refusal or the sign-in
it needs. Software on a site is installed by JARVIS through relay's `install`
(or a `run`'s install step), from the site's Spack, modules and MPI, which is
what JARVIS tracks; the site's system packages (`apt`, `dnf`, `yum`, `brew`)
are its admins'.

A site the person names that is not in `describe`'s list, or the first site
of all, is one the person adds on the Compute page; `describe` lists it from
then on.

## Reads never ask

Four tools only read: `describe`, `exec_read`, `files_read` and
`packages_read`. They change nothing and never ask the person, so they suit
planning too; `exec`, `files` and `packages` are for changes.

- `describe` lists sites, describes one (`site`: its routes, whether its
  JARVIS root is set up, and the packages the root holds) and observes a job
  or a service (`job`; for a service it gives the endpoint and whether it is
  ready).
- `packages_read(site=...)` lists the packages the site's JARVIS root holds,
  as the site lists them now: each one's version, review digest, summary,
  parameters, repository directory, files and git source. `match` keeps those
  whose name, title or summary holds every word (`match="lammps"`).
  `packages` has no list: it only adds a repository.
- `exec_read` runs one read-only command, given as an argument list with no
  shell: listings and file reads (`ls`, `cat`, `head`, `tail`, `grep`,
  `stat`, `du`, `df`), the scheduler (`squeue`, `sinfo`, `sacct`,
  `scontrol show`), the machine (`hostname`, `nproc`, `uname`), modules and
  quotas, Spack queries (`spack find`, `spack info`) and the JARVIS reads
  below. Anything else is refused with `policy_refused` and the next step
  `exec`.
- `files_read` lists, stats, reads and checks files (`op` list, stat, read,
  has).

## describe

Without arguments `describe` lists the sites, by the names the other tools
take; with `site` it describes one site and its routes.

## Read what the site knows about itself

A site's facts are the site's own, not relay's or this skill's. The ones that
bear on a queue, a node count, storage or an MPI for a run are in
`describe(site=...)`:

- `facts.sched` is JARVIS's scheduler report for the site: its provider,
  account and `site_skills`. The partitions it reports (nodes, idle nodes, CPUs
  and memory per node, time limits) are the result's `partitions`, and the MPI
  JARVIS found is its `mpi`. Before relay has placed JARVIS on a site, the
  same partitions come straight from the scheduler (`facts.sched.source` is
  `sinfo`, read at `observed_at`); once JARVIS is placed, `describe` gives
  JARVIS's report. Idle nodes change by the minute, so an old answer's idle
  counts are stale. A run's card also keeps its partition's facts as they were
  when the card was made, in `result.partition_facts`.
- `facts.resource_graph` is the site's JARVIS resource graph: where it is, its
  `source`, and under `net` the data and control networks JARVIS launches MPI
  on. A graph the site publishes (`source` `site`, named by the site's
  `$JARVIS_RESOURCE_GRAPH`, or `setting`) is the site's own and offers no
  `collect`. Relay's own graph (`source` `relay`) offers `collect`, a job on
  the site that fills an empty `net`. A `net` in JARVIS's older list form
  reads `form: legacy_list` with the advisory `resource_graph_net_legacy`: the
  net is there, and the first multi-node launch collects it again into relay's
  own home, not into the site's file.
- A site skill is what the person or the site's admins wrote down about the
  machine. `facts.sched.site_skills` lists them; the JARVIS command below
  reads one (`rg skill show NAME +json`).
- The site can also carry the person's own guide in relay. The result then
  has a second text block holding it, and `skill.text` reads `(below)`; when
  relay cannot find the guide, the `skill` field says so. Relay also serves
  guides as MCP resources (`relay://sites/<site>/skill`,
  `relay://skills/<name>`); `files` refuses `relay://` URIs, and `describe`
  reads them.

A site fact changes through JARVIS on the site with `exec`, giving
`facts.jarvis.exec` followed by JARVIS's own arguments, such as `rg net set
--data <network> --reason "..." +json` or `rg skill set NAME --text "..."
+json`. A recorded fact is one the person confirmed, and `--set_by` says who.
On a guarded site, `exec` takes a `plan` that says what the command changes,
and relay asks the person before it runs. What `ls`, `module` or interface
listings would show by hand, JARVIS already reports.

To read site facts, give `exec_read` `facts.jarvis.read` followed by exactly
one of `sched info +json`, `rg facts show +json`, `rg skill list +json` or `rg
skill show NAME +json`. These run with no shell and no `plan`, even on a
guarded site. Anything else, answers included, goes through `exec` with
`facts.jarvis.exec`.

## Run work

- `run` submits a job as a PSI/J JobSpec. When CLIO supports tasks it returns
  a task; otherwise it waits up to `wait_s` and returns the operation, which
  `describe(job=...)` observes.
- `exec` runs one short command on the site's login side and returns bounded
  output. `exec_read` covers commands that only read.
- `files` writes, stages and removes small files; `files_read` reads them. A
  file on this machine, such as a person's STL or a result to open locally,
  moves with `files(op="upload", local_path=..., path=...)` or
  `files(op="download", path=..., local_path=...)`, at any size. Relay streams
  the bytes itself, checks the SHA-256 on the site and returns only metadata:
  the result's `sha256` and `verified` say it arrived. `content_base64` chunks
  carry every byte through the conversation instead. `local_path` is absolute
  on the machine relay runs on; when relay cannot open it, the refusal says
  so, and the person has to make the path reachable for relay. `stage`
  returns the SHA-256 a JobSpec input names. A package parameter set to the
  input's name (such as `body.stl`) gets the staged file: relay puts in its
  path on the site.
- `serve` starts a job that serves ports. Its task completes when the service
  is ready, with the endpoint in the result, while the service keeps running
  until it is stopped. Each port in the endpoint has an `address` (`host:port`)
  for the client. The port is the one the service bound, as JARVIS reports it.
  The task completes within seconds of the service coming up, while its job
  still runs, and a short job may end soon after. The task ending at ready says
  the service is up, not that the run is done.
  `serve(service=<operation>, until="steps")` waits for the run. With tasks it
  returns the task `<operation>.steps`, which completes when every compute
  step has ended, or the job has, and carries `until` and the operation's
  outputs; CLIO wakes the conversation when it completes. Without tasks it
  waits up to `wait_s` (at most 300 s), and `until.ended` says whether the run
  is over. Where `serve` has no `until`, a live view's `watch_steps` returns
  when the run is `complete` or `finished`, and relay sends a notice when the
  operation changes. See "Long runs and failed runs".
  One package can serve beside a run, such as pvserver beside gray_scott, in
  one `serve` pipeline, with each step's `host_slice` parameter placing it on
  its own nodes of the job (a `start:end` range of node indices), the service
  on the nodes it needs and the solver on the nodes its layout was sized for,
  without overlap. JARVIS decides which step serves from each package's
  deployment profile.
- The order of a pipeline's packages is the order JARVIS starts them in, not
  the way data moves: a service starts before the solver that feeds it. The
  direction is in the job card's `couplings` (each `from` feeds its `to`) and
  the components' order there, which is producer first: gray_scott feeds
  pvserver, so gray_scott --> pvserver. Relay fills the couplings from the
  packages' contracts; a job's own `couplings` cover what a contract cannot
  say, such as two solvers where one reads the other's output.
- A service package's `linger` keeps it serving after the run ends (pvserver:
  180 s by default), so a following view can draw the run's last steps and the
  person can look at the final output. At 0 the view loses the steps it had
  not drawn. `cancel(operation=<the serve operation>)` once the view has the
  last step (the live view's `watch_steps` returns `complete` or `finished`)
  ends the linger at once and frees the nodes; the view keeps its last
  picture, and relay's own confirm asks the person. Otherwise the linger ends
  by itself.
- A run does not wait for its viewer. A package whose output a live view
  follows writes each step whole as it comes (to a temporary name, then
  renamed) and goes straight on: the view reads whatever is on disk when it
  attaches, so early steps are not lost. A ready marker, a gate or a pause
  that holds the run until a view attaches stalls it when none does, and a
  timeout that fails it then fails a good run. Anything a package does wait
  on is best judged by progress, not by a time limit: it says what it waits
  on and fails only when that stops changing.
- Runs write under the site's outputs directory, `describe`'s
  `info.facts.outputs_dir`, which `site_clean` keeps, and a package's
  `run_dir` defaults to it. Relay refuses a job that names a path under its
  own directory (`~/.clio-relay`).
- When another of relay's services still runs on the site, such as a viewer
  kept up for review, the new `run` or `serve` asks the person whether to end
  it when the new job is submitted. The ask is relay's own.
- When relay cannot bring a running service to this machine, the result is an
  error with `result.service_error`, whose `reason` says why, while the job
  runs on. `host_key_unverified` means ssh could not check the compute node's
  host key, a check the person's ssh setup owns; a retry meets the same check,
  and the message says what the person would need to look at. `cancel` stops
  the job.

A refusal carries a typed reason in `structuredContent.refusal`. A site that
needs sign-in, a missing account or an unreachable host is the person's to
fix; a retry meets the same refusal.

When JARVIS refuses a pipeline, `refusal.data.issues` lists its typed issues,
each with `kind`, `field` and `message`, and `refusal.data.kinds` names them.
`configuration_rule_violated`, `host_slice_invalid`, `host_slice_overlap`,
`start_mode_invalid` and `service_port_conflict` name a parameter to change.
`service_after_batch` and `service_blocks_pipeline` mean the steps are in the
wrong order or role for a serve. `package_unloadable` and
`deployment_contract_invalid` are faults in the package itself.

## Size the layout from the problem and the partition

Choose how many nodes and ranks a run takes from the problem and the machine.
No node count, rank count or scale is a default: a right size on one machine
is a handful of nodes and on another a thousand, so every count you consider
or offer is derived from the facts below.

- Settle what the question needs physically before sizing: the resolution,
  the simulated time or steps, the accuracy that makes the result answer it.
  Sizing finds the compute that delivers them. When time or budget is short,
  scale the compute first; a coarser grid or a shorter simulated time changes
  the answer, so bring it to the person as a different question, not as a way
  to make the job fit.
- Start from the problem's own parallel units: k-points, pools, images,
  replicas, bands, domains or a process grid, whatever the application splits
  its work by (its package's `sizing` and decomposition controls say which).
  They bound the range: the fewest ranks whose share of the problem fits in
  memory, up to the most that still each get useful work, and which counts
  divide the units evenly. Work that needs nothing another part produces
  (independent stages, cases, ensemble members) is a parallel unit at the
  level of jobs: in series in one job the parts take the sum of their times,
  as separate jobs side by side the time of the longest. Size such jobs
  together, their combined nodes against the queue's limits and idle nodes
  and their node-hours against the budget.
- Set that range against the queue: from `describe`, each partition entry's
  `nodes` and `idle`, `physical_cores` and `memory_mb` per node, its time
  limit (`max_time`, `max_time_s`), and the queue's own per-job node limits,
  `min_nodes` and `max_nodes`, the fewest and the most nodes one job may take,
  which some queues set well above one. The entry's `limits` holds every
  limit the scheduler reported, exactly as it reported it, and
  `limits_source` says which command and field each came from.
- Unknown is not unlimited. `"UNLIMITED"` in `limits` is the scheduler saying
  there is no limit; a key named in `limits_unknown` (or a whole entry with no
  `limits`) is one relay could not read, so its null says nothing. For an
  unknown limit that matters to the layout, check the site's documentation of
  its queues or ask the person, and never assume a queue takes any size or any
  time. A layout that fills whole
  nodes, divides the units evenly, fits each rank's memory and sits inside
  the queue's limits is a candidate; idle nodes say how soon it can start.
- When the person's budget or allocation is known (node-hours left, a
  reservation, a cap they gave), it bounds the range too.
- A pilot is a sample of the application, not a rehearsal of the production
  run: it measures how the code uses compute, so what it finds carries to
  layouts it did not run. Measure the cost of a unit of work (a step over
  each rank's share of the problem, or whatever the work grows with), how
  that cost changes across ranks and nodes, the startup and the output
  writes. The code or its documentation can say how its work should scale; a
  real run gives the constants and shows what that reading missed. Pilot at
  two or more sizes inside the queue's limits, far enough apart to show the
  scaling and toward the range you would offer, each long enough that the
  cost per step has settled past startup.
- A timing measures the code only when nothing else shares its resources:
  schedulers such as Slurm give a job's free cores and memory bandwidth to
  other jobs unless it keeps its nodes. Run a pilot, and any run you will
  size from, with `resources.exclusive_node_use: true`. Before relying on a
  pilot's timings, check they are believable: settled rather than drifting,
  ordered across sizes the way the code should scale, in line with earlier
  runs of the same setup. A timing that fails this is not a measurement:
  find why and measure again.
- Then offer the person a choice of node counts spanning the sensible range
  for this problem on this machine, each with its projected time to result
  and the node-hours it costs, and say how far you trust each projection.
  Let the person pick; the
  time request for the chosen one follows the next section.

## Ask for enough time

Size a job's time request from what was measured, then pad it generously.
The request is (startup overhead + measured run time) x a safety coefficient,
and every term in it comes from a measurement:

- When nothing has measured this application on this build and site, run a
  short pilot first (a few steps or iterations, in a short job), and size
  production from what the pilot measured. An estimate of the run time (from
  the application's documentation, a similar case, or your own reckoning)
  never becomes the time asked for, however much it is padded: a guess times
  two is still a guess. If the person cannot wait for a pilot, say the
  request is unmeasured and let them choose.
- Projected wall time = measured startup overhead (activating the package's
  environment and any service started beside it becoming ready) + steps x
  seconds per step + output writes, all from a pilot or an earlier run of the
  same build. Take the overhead from the run record's `phase_timings`:
  `before_first_step_seconds` plus each service package's `ready_seconds`.
  Only a record without phase timings falls back to the gap from the job's
  start to its first step; never guess the overhead.
- Project any candidate layout from those measurements: production's work
  shared over that layout's ranks, at the measured cost per unit and the
  measured scaling, plus startup and output. A plain ratio of one pilot's
  seconds per step is not a projection: fixed per-step work and communication
  keep a smaller run from getting proportionally faster and a larger one from
  staying on the line, which the measured scaling captures. Trust a
  projection closely inside the range the pilots covered, less the further it
  extrapolates, and less again for a change no pilot exercised (another
  decomposition shape, a share per rank that no longer fits memory as it
  did); when the chosen layout rests on a long extrapolation and the run is
  costly, a pilot point nearer it is worth its short job.
- Request the measured projection times a safety coefficient, rounded up.
  Size the coefficient from how far the measurement can be trusted: larger
  when it rests on one short pilot, when steps varied, when production
  runs longer than anything measured, or when its layout is projected far
  from the measured ones, and smaller when several runs of the
  same setup agree; always generous, and say which coefficient you chose and
  why. The coefficient covers the spread of a measured run; it does not stand
  in for a measurement.
  Overallocate rather than cut it close: a job killed at its limit loses its
  unfinished work, and schedulers such as Slurm charge the time a job used,
  not the time it asked for, so a job that ends cleanly before its limit
  costs nothing for the rest. A longer request can wait a little longer in
  the queue.
- An application's own time limit (a stop timer in its input, after which it
  writes a restart and exits cleanly) is sized from the time request, not
  apart from it: set it just under the request, leaving room for that last
  write (the time a restart write took in the pilot or an earlier run, padded
  like the rest of the request).
  Never set it below the projected run time. The time request is the
  person's budget, and a second, shorter limit stops a run that was on
  track. Leave the application's default when nothing needs the clean stop.
- Say so in the spend approval: the projected time, the coefficient, the
  padded request, and that unused time is not charged when the job ends
  cleanly.
- If the padded request exceeds the partition's time limit (in
  `partitions`), say so and propose options for the person to pick: more
  nodes, projected from the measured scaling, as far as the site and the
  budget allow; another partition with a longer limit; a run that writes a
  restart and continues in a following job, when the code can. A shorter or
  coarser run changes what the run answers; offer it only said that way. Do
  not trim the coefficient to fit the limit.

A package's contract can say how to project its own run; the padding and the
approval above still apply.

## Packages are applications, cases are inputs

A package is one application, written generically, and takes that
application's own input: a LAMMPS script, a namelist, a settings file, an
input bundle. The case the person asks for (an obstacle in a channel, a
protein in water, a wing at an angle) is that input; it is not a package.
`packages_read(site=..., match="<application>")` shows whether the site's
root already holds a package for the application, and its `contract.yaml`
(its parameters say which input it takes; `files_read` reads it under the
package's `repo_dir`) says how the case goes in. The `jarvis-package` skill
covers writing one; a package built around one case serves that case only. A
site relay set up has no jarvis-cd `builtin.*` packages: they are written for
a person to drive and hardcode a case or a site's setup, so relay removes that
repository. Its packages come from clio-jarvis and the person's own
repositories. A builtin package in jarvis-cd's repository (`builtin/` in
grc-iit/jarvis-cd) still shows how an application installs and launches,
while every site fact (MPI, launcher, nodes, paths) comes from the resource
graph and JARVIS, as the `jarvis-package` skill says. How a case was written
can become a skill of the person's own, for when they want it again.

## A site's packages

`run` takes a JARVIS package by name, `package: {name, parameters}`, named
`<repository>.<package>`, and runs only a package the site's JARVIS root
holds. Relay sets that root up once per site, with jarvis-cd and clio-jarvis
at the commits its release pins. Setting up is `install`'s first step: a
`run`, `serve` or `install` on a site that is not set up refuses and names
that step, and `describe(site=...)` says beforehand whether the site is set
up. A root at other pins, including JARVIS placed any other way, is not set up
either; the refusal and the ask say which pins it holds and which relay brings
it to (`Update JARVIS on <site>?`).

A package the person wrote reaches the site with `files`: its repository,
laid out `<name>/<name>/<package>/pkg.py`, copied into the person's space on
the site, then registered with
`packages(op="add", site=..., path="<that directory on the site>")`. It runs
`jarvis repo add` in the site's root (`force: true` replaces a repository of
that name) and lists the site's packages again. A git push would publish the
person's package somewhere else; `files` keeps it between this machine and
the site.

Adding runs nothing. Each package's review identity is its digest, computed
on the site from the package as it sits in the root; on a guarded site the
person reviews that digest before its first run there, and an edit is a new
digest that is reviewed again. A job's packages that are not reviewed yet come
as one review, so one yes covers a pipeline.

## Install ahead of a run

When the person wants a package's software on a site before running it ("install
gray_scott on ares, don't run anything yet"),
`install(site=..., package={name, parameters})` takes the same `package` a
run takes. It is `run`'s install step on its own, and nothing launches:

- A site that is not set up gets its JARVIS root first, after the person says
  yes; `install` does this itself.
- JARVIS checks what the site has where the site chose (below): on the login
  node under JARVIS's limits, or inside a short job on the compute nodes, and
  the task waits while that job queues and runs. Later installs and runs of
  the same packages read the check's record and skip it until the site
  changes. When everything is there, the operation completes with `installed`
  and nothing is built.
- When JARVIS only has a question (which MPI) and the software is already
  there, the person answers the question and nothing else: relay checks again
  with the answer and the operation completes with nothing built.
- When something is missing, the person gets the same asks a run's install
  gets: approve the install and answer any question JARVIS has (below),
  including where it builds. JARVIS then builds it where the site chose and
  checks again, and the operation completes. The approval names the
  provider Spack picked for each virtual dependency, such as fftw 2.1.5 for
  fftw-api. In a compute job, the approval names the job's wall time: the
  build times JARVIS measured at the site, or the partition's limit when part
  of the build was never timed there. A build longer than one job needs
  another `install`, which builds only the rest, and the approval says so. On
  the login node, JARVIS's own install runs there under the limits JARVIS
  sets, as a background task with progress and no time limit: a long build is
  expected, and it runs until it is done or `install(cancel=...)` stops it.

Like `run` it is a task, followed with the task or with `describe(job=...)`
and cancelled with `install(cancel=...)`. One `install` call can list several
packages in `packages`, such as everything a plan runs, the same steps the
later `run` or `serve` takes. The person then gets one review of the
packages, one set of JARVIS questions and one build, instead of one of each
per package. A later `run` of the same packages finds the software installed
and goes straight to its job.

## Questions JARVIS asks

JARVIS asks what it cannot decide alone, and relay turns each question into an
ask for the person: the task turns `input_required` with the question and its
choices, and the person's answer moves it on. JARVIS keeps the person's
answers for the site, so a later install does not ask again unless the person
wants to change one.

- **Which MPI.** An install with several MPI candidates asks once for the
  site. Installs started together on one site share that question: one answer
  moves on every install that asked.
- **Where checks and builds run.** JARVIS asks, once per site, whether its
  software checks (or builds) run on the login node under JARVIS's limits, in
  a compute job, or are asked each time. The question carries JARVIS's
  recommendation and its evidence (the login node's load, the queue wait, the
  cost of each package), and may offer a choice for one package only, such as
  a long build in a compute job while the rest check on the login node. The
  limits are JARVIS's. Builds are offered the same way as checks: relay has
  no default of its own, so a site that has not answered shows JARVIS's
  recommendation. An answer marked for this run only is asked again next
  time.
- **Which Spack.** When JARVIS has no Spack on the site, the install asks which
  of the site's own Spack checkouts to use. Each candidate also has a
  `prepare` command that makes a JARVIS Spack chained to it as an upstream,
  which suits a person who cannot write to the site's own. It is
  `facts.jarvis.exec` followed by `spack prepare --root
  <facts.jarvis.spack_root> --site_spack <root> +json`, run with `exec`; the
  same `run` then finds it. Exit 3 with `ambiguous_compiler` lists the
  compilers to choose from, and `--compiler` gives the choice (the `spack`
  skill has the details).
- **How a package installs.** JARVIS owns the install method: Spack, pip
  (into a venv JARVIS keeps for the pipeline), conda (into an env from a conda
  JARVIS finds, or the Miniforge it offers to install in the site home), or a
  container (pulled with the site's engine, rootless podman or Apptainer,
  never a shared Docker daemon). Relay passes whichever JARVIS resolves
  through the same `install` ask, and the ask says which method each package
  uses. When a package offers several methods that fit the site, or JARVIS
  cannot tell which python, conda or engine to use, it asks (`install_method`,
  `python_missing`, `conda_missing`, `conda_select`, `container_engine`) with
  its candidates. MPI and compiled HPC codes come from the site's Spack and
  modules: JARVIS refuses a pip or conda MPI (`mpi_from_package_manager`),
  since such an MPI does not span nodes on the site's fabric, and one put in
  place with `exec` is one JARVIS does not track. A failed install says its
  method and kind (`pip_install_failed`, `conda_install_failed`,
  `container_pull_failed` and the like) with JARVIS's remedy.
- **Moving a queued job.** When a job's start is far off and another
  partition would take it now, relay asks the person whether to keep waiting
  or move it, and JARVIS moves the same job on their answer; a cancel and a
  new run would be a new job at the back of the queue. When JARVIS refuses
  the move, the message says why.

With a job's queue unset (`attributes.queue_name`, or a package's `queue`
parameter), the site's default applies.

## Site facts JARVIS is unsure of

JARVIS decides deployment details, such as the network MPI launches on, with
fixed rules over the facts it collected, and says nothing when its pick is
sure. When a pick rests on something it cannot settle alone, it raises a
`site_fact_uncertain` issue instead of guessing. The adaptive part is finding
out what this cluster really does and proposing a value; the person decides,
and JARVIS checks and records the answer. The network and site logic stays
JARVIS's.

The issue can reach you in a run's `refusal.data.issues` or `result.issues`,
in `ppl check` output, in a task's question, or in `rg facts show +json`, which
is read-only and lists every open question and recorded answer. Its fields:

- `severity`: `block` stops the submit; `advisory` lets the run go ahead
  with JARVIS's pick.
- `details.reasons[]`: what is uncertain, and the `consequence` of each.
- `candidates[]`: the ranked options, and `why` each one ranks there or is
  excluded.
- `details.evidence`: the per-node facts the question rests on.
- `details.pick`: what JARVIS would use, and `consequence_if_wrong`.
- `details.probes[]`: read-only commands, each with the `why`.
- `details.answer`: the accepted values and the command form.
- `details.previous_answer`: when the evidence changed since the person last
  answered, their old answer.

What helps settle one:

- The issue's own `details.probes` and the site's skills
  (`rg skill show NAME +json`), set against `details.evidence`. The probes run
  through `exec_read`, or `exec` for one it refuses; on a guarded site, `exec`
  takes a `plan` that says the command is a read-only probe, and relay asks
  the person before it runs. The login node is for light, short probes;
  anything that must see compute nodes, or takes longer, runs in a JARVIS
  job, such as the two-node smoke run the probes name (`jarvis ppl submit`).
- A proposal the person can judge: the value (`accept` for JARVIS's pick, or
  a value of the form `details.answer` lists), the evidence for it, what
  `consequence_if_wrong` says would happen if it is wrong, and any
  `previous_answer` with what changed.
- The answer, once the person confirms it, is recorded with
  `facts.jarvis.exec` followed by `rg facts answer <issue_id> --value <value>
  --reason "<evidence>" --set_by <person> --proposed_by <agent> +json`, with
  the `issue_id` from the issue and a `plan` on a guarded site.
  - `site_fact_answer_stale` means the evidence changed: the issue named by
    `details.current_issue_id` is the current one.
  - `site_fact_answer_invalid` means JARVIS refused the value, and says why.
- After that, the check or the same `run` uses the confirmed value, and
  JARVIS stays silent until the evidence changes.

An advisory issue does not hold the run. Its consequence matters when the
person asks, or when the run is slow or failing in the way the issue
describes. `rg facts forget <fact> +json` drops a recorded answer, so JARVIS
asks again.

## Long runs and failed runs

An install, the queue and the run itself can take hours. When `run` or
`serve` returns a task, CLIO wakes the conversation when the task ends or
needs the person, so a turn can end there. Waiting is event driven, so polling
of any form only adds noise and cost: `describe` in a loop, repeated `exec` or
`cat` reads of a result file or log, scheduler queries such as `sacct` or
`squeue`, or a `run_code` script that loops over any of these with sleeps. A
file that is not there yet reads as a failed command, so such a loop fills
the conversation with failures. A `serve` task ends at ready while its run
goes on; `serve(service=<operation>, until="steps")` carries the operation's
outputs when the run ends, so the run's result file needs no separate read.
Some sites run Slurm without accounting, where `sacct` always fails; relay's
operation state is the job's state there. A job waiting in the queue says so
in the operation's `result.queue` and message, with its estimated start.

Whenever you are woken or look at a run still going, check its pace against
what the person needs. A package that reports its steps gives it in
`result.progress.data.pace`: `seconds_per_step` (startup left out),
`latest_seconds_per_step`, and with a total `projected_end_at`,
`time_limit_ends_at` and `limit_margin_s` (negative when the time limit ends
the job first); the task's status says the same in words. Without a pace,
take the rate once from the times the run printed for its steps. For work of
uncertain length (a relaxation that converges), estimate the steps the
problem plausibly needs. When the projection lands past the time limit, or
costs far more than the person meant to spend, bring them the decision early,
while the remaining time can still change the outcome: a layout across more
of the site's nodes from the work's parallel units, restarting from its
latest restart point when it writes one; a partition with a longer limit; or
stopping. Say the measured rate and the projection. Waiting on is one of
those options for the person to choose, not one taken for them by silence.

When a run fails, `result.issues`, JARVIS's typed issues, usually says more
than the logs. Each names its `kind` and the field it is about. An
`mpi_network` issue means the ranks could not reach each other on the network
JARVIS launched them on: it names the resource graph field and the networks
the nodes share. The fix is the network the issue points to (or, on relay's
own graph, the resource graph job that collects them again), recorded with
`rg net set` once the person confirms it; every later job on the site uses
it.

When an install job fails, the operation ends `failed` as a failed run job
does, with the job's `exit_code`. Its message is JARVIS's line for each failure,
naming the package Spack was building, and `result` holds JARVIS's records in
`failures` and `issues`, the job id in `install_job`, and in `install_log` the
whole log on the site, which `files_read(op="read")` reads. A fix belongs in
the place that owns the cause (a package parameter, the person's answer to a
JARVIS question, the site's JARVIS Spack through `spack prepare`), and the
same `run` then picks it up. The real decisions in it, such as a choice
between two compilers or a larger allocation, are the person's.

A fact JARVIS holds about the site that turns out wrong is corrected in
JARVIS once the person confirms it: the network with `rg net set`, anything
else as a site skill with `rg skill set`.

## Stop a service, clean a site

`cancel(operation=...)` stops a service or cancels a job. Relay confirms a
stop with the person itself, naming the service and the nodes it releases, so
a question of your own before `cancel` asks the person twice.

`site_clean(site=...)` removes relay's deployment from a site, so the next use
deploys it again. It asks the person first and keeps the site's Spack store
and JARVIS's recorded answers (which MPI, which compiler). It removes nothing
while relay's jobs still run there, as the site's scheduler reports them, and
its refusal names each job and its operation, which `cancel(operation=...)`
ends. `cancel` also ends a job the scheduler still lists under an operation
that already ended. `forget_decisions=true` also forgets those answers, so the
next install asks them again; JARVIS's `ppl install --forget <selector>`, run
with `exec`, forgets one. A person who wants to start from nothing, so the
next install asks which MPI and where installs run again, is asking to forget
those answers. What relay's runs wrote, under the outputs directory or
elsewhere under the person's home, is the person's: the clean names those
outputs in its question and keeps them, and the result lists them as
`outputs_kept`; `remove_outputs=true` deletes them too. Relay's tools cover
all of this without the `clio-relay` command line.

## Sites are the person's

The person manages sites on the Compute page or with `clio-relay site` on the
command line; relay's tools do not add, edit or remove them.
