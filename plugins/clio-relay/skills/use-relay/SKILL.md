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

## Read what the site knows about itself

A site's facts are the site's own, not relay's or this skill's. Before you
choose a queue, a node count, storage or an MPI for a run, read them from
`describe(site=...)`:

- `facts.sched` is JARVIS's scheduler report for the site: its provider,
  account and `site_skills`. The partitions it reports (nodes, idle nodes, CPUs
  and memory per node, time limits) are the result's `partitions`, and the MPI
  JARVIS found is its `mpi`.
- `facts.resource_graph` is the site's JARVIS resource graph: where it is, and
  under `net` the data and control networks JARVIS launches MPI on. When `net`
  is empty, `collect` gives the job that fills it in; offer it to the person
  and run it once they agree.
- A site skill is what the person or the site's admins wrote down about the
  machine. `facts.sched.site_skills` lists them; read one with the JARVIS
  command below (`rg skill show NAME +json`).
- The site can also carry the person's own guide in relay. The result then
  has a second text block holding it, and `skill.text` reads `(below)`. When
  the `skill` field says relay cannot find the guide, tell the person. Relay
  also serves guides as MCP resources (`relay://sites/<site>/skill`,
  `relay://skills/<name>`); `files` refuses `relay://` URIs, so use
  `describe`.

To change a site fact, run JARVIS on the site with `exec`, giving
`facts.jarvis.exec` followed by JARVIS's own arguments, such as `rg net set
--data <network> --reason "..." +json` or `rg skill set NAME --text "..."
+json`. Do it only after the person confirms the fact, and say who
confirmed it with `--set_by`. On a guarded site, give `exec` a `plan` that
says what the command changes; relay asks the person before it runs. Do not invent facts about a site, and do not
work them out by hand with `ls`, `module` or interface listings when
JARVIS already reports them.

To read site facts, give `exec` `facts.jarvis.read` followed by exactly one of
`sched info +json`, `rg facts show +json`, `rg skill list +json` or `rg skill
show NAME +json`. These run with no shell and no `plan`, even on a guarded
site. Anything else, answers included, goes through `facts.jarvis.exec`.

## Run work

- `run` submits a job as a PSI/J JobSpec. When CLIO supports tasks it returns
  a task; otherwise it waits up to `wait_s` and returns the operation, which
  `describe(job=...)` observes.
- `exec` runs one short command on the site's login side and returns bounded
  output.
- `files` lists, reads, writes and stages small files. `stage` returns the
  SHA-256 a JobSpec input names. To hand a staged file to a package, set the
  package parameter to the input's name (such as `body.stl`); relay puts in its
  path on the site. Never write a directory placeholder around it.
- `serve` starts a job that serves ports. Its task completes when the service
  is ready, with the endpoint in the result, while the service keeps running
  until it is stopped. Each port in the endpoint has an `address` (`host:port`):
  hand that to the client. The port is the one the service bound, as JARVIS
  reports it; never choose one yourself.
  To serve one package beside a run, such as pvserver beside xcompact3d, give
  both in one `serve` pipeline, with each step's `host_slice` parameter placing
  it on its nodes (pvserver `0:2`, xcompact3d `2:6`, say). JARVIS decides which
  step serves from each package's deployment profile.

A refusal carries a typed reason in `structuredContent.refusal`. Read it and
act on it: a site that needs sign-in, a missing account or an unreachable host
are things to tell the person, not to retry.

When JARVIS refuses a pipeline, `refusal.data.issues` lists its typed issues,
each with `kind`, `field` and `message`, and `refusal.data.kinds` names them.
`configuration_rule_violated`, `host_slice_invalid`, `host_slice_overlap`,
`start_mode_invalid` and `service_port_conflict` name a parameter to change:
change it and call again. `service_after_batch` and `service_blocks_pipeline`
mean the steps are in the wrong order or role for a serve. `package_unloadable`
and `deployment_contract_invalid` are faults in the package itself: tell the
person.
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

## Questions JARVIS asks

JARVIS asks what it cannot decide alone, and relay turns each question into an
ask for the person: the task turns `input_required` with the question and its
choices. Relay the question as it is and do not answer it yourself. JARVIS
keeps the person's answers for the site, so a later install does not ask again
unless the person wants to change one.

- **Which MPI.** An install with several MPI candidates asks once for the
  site.
- **Which Spack.** When JARVIS has no Spack on the site, the install asks which
  of the site's own Spack checkouts to use. Each candidate also has a
  `prepare` command that makes a JARVIS Spack chained to it as an upstream,
  which is better when the person cannot write to the site's own. To prepare,
  run `facts.jarvis.exec` followed by `spack prepare --root
  <facts.jarvis.spack_root> --site_spack <root> +json` with `exec` once the
  person agrees, then call the same `run` again. Exit 3 with
  `ambiguous_compiler` lists the compilers to choose from: ask the person, run
  it again with `--compiler`, and do not pick one yourself.
- **Moving a queued job.** When a job's start is far off and another
  partition would take it now, relay asks the person whether to keep waiting
  or move it, and JARVIS moves the same job on their answer. Do not cancel and
  rerun to switch partitions yourself. When JARVIS refuses the move, the
  message says why.

Leave a job's queue unset (`attributes.queue_name`, or a package's `queue`
parameter) unless the person names one: the site's default applies.

## Site facts JARVIS is unsure of

JARVIS decides deployment details, such as the network MPI launches on, with
fixed rules over the facts it collected, and says nothing when its pick is
sure. When a pick rests on something it cannot settle alone, it raises a
`site_fact_uncertain` issue instead of guessing. Your part is the adaptive
one: find out what this cluster really does, propose a value, and let the
person decide. JARVIS checks and records the answer; you add no network or
site logic of your own.

The issue can reach you in a run's `refusal.data.issues` or `result.issues`,
in `ppl check` output, in a task's question, or in `rg facts show +json`, which
is read-only and lists every open question and recorded answer. Read these
fields:

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

For a blocking issue, work through these steps:

1. **Investigate.** Run the issue's own `details.probes`, read the site's
   skills (`rg skill show NAME +json`), and compare what you find with
   `details.evidence`.
   - Run every probe through `exec`.
   - Only light, short probes run on the login node. Anything that must see
     compute nodes, or takes longer, runs in a JARVIS job, such as the
     two-node smoke run the probes name (`jarvis ppl submit`).
   - Do not run commands the issue does not offer, and do not reach compute
     nodes any other way.
   - On a guarded site, give `exec` a `plan` that says the command is a
     read-only probe; relay asks the person before it runs.
2. **Propose.** Tell the person:
   - which value you propose (`accept` for JARVIS's pick, or a value of the
     form `details.answer` lists);
   - the evidence for it;
   - what `consequence_if_wrong` says would happen if the choice is wrong.

   If there is a `previous_answer`, name it and what changed. Then wait for
   the person to confirm. Never answer for them.
3. **Record.** Once they confirm, run `facts.jarvis.exec` followed by `rg facts
   answer <issue_id> --value <value> --reason "<evidence>" --set_by <person>
   --proposed_by <agent> +json`. Use the `issue_id` from the issue. Give
   `exec` a `plan` on a guarded site.
   - `site_fact_answer_stale` means the evidence changed: read the issue
     named by `details.current_issue_id` and propose again.
   - `site_fact_answer_invalid` means JARVIS refused the value: tell the
     person why, and do not work around it.
4. **Continue.** Re-run the check or call the same `run` again. JARVIS now
   uses the confirmed value and stays silent until the evidence changes.

An advisory issue does not hold the run. Mention it to the person with its
consequence. Investigate and propose an answer the same way only when it
matters: when the person asks, or when the run is slow or failing in the way
the issue describes. If the person wants JARVIS to ask again,
`rg facts forget <fact> +json` drops the recorded answer.

## Long runs and failed runs

An install, the queue and the run itself can take hours. When `run` or
`serve` returns a task, say what you are waiting for and end your turn: CLIO
wakes you when the task ends or needs the person, so do not poll `describe` in
a loop. When you are woken, carry on with the next step of the plan the person
approved. A job waiting in the queue says so in the operation's
`result.queue` and message: pass the estimated start on to the person.

When a run fails, read `result.issues`, JARVIS's typed issues, before the
logs. Each names its `kind` and the field it is about. An `mpi_network` issue
means the ranks could not reach each other on the network JARVIS launched
them on: it names the resource graph field and the networks the nodes share.
Do not stop at the diagnosis. Propose the fix to the person (the network the
issue points to, or the resource graph job to collect them again), record it
with `rg net set` once they confirm, and call the same `run` again. Every
later job on the site uses it.

When an install job fails, the run fails `submit_failed` with
`refusal.data.needs: "jarvis ppl install"`. Its message ends with the last part
of the install log, and `refusal.data.install_log` is the whole log on the site:
read it with `files(op="read")`. Find the cause, fix it in the place that owns
it (a package parameter, the person's answer to a JARVIS question, the site's
JARVIS Spack through `spack prepare`), and call the same `run` again. Ask the
person only for a real decision, such as a choice between two compilers or a
larger allocation.

When a fact JARVIS holds about the site turns out wrong, propose the change to
the person and record it with JARVIS once they confirm: the network with `rg
net set`, anything else as a site skill with `rg skill set`.
## Sites are the person's

Do not add, edit or remove sites. The person manages them on the Compute page
or with `clio-relay site` on the command line.
