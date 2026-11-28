---
name: hpc-batch-jobs
title: Run and Wait on Slurm Batch Jobs Safely
description: Use to submit Slurm jobs and wait on them in bounded, low-output steps, reporting every job id.
keywords:
- level:L2
- slurm
- hpc
---

`sbatch --parsable` prints the job id. A job id recorded in the workspace at
submission (for example `jobs/job_ids.txt`, with the submit time and the script
path) survives a lost context or a failed wait.

This skill is for jobs submitted on the machine CLIO runs on. A job on a remote
site, such as a cluster reached over SSH, goes through relay (`clio-relay`'s
`run`, `install` or `exec`), never through `ssh` in a shell. A job that relay's
`run` or `serve` started is waited on through relay (its task, or `serve`'s
`until="steps"`), not with this helper or `sacct`.

The bundled helper waits in bounded steps. `SKILL_ROOT` is the skill directory
reported by `load_skill`:

    bash SKILL_ROOT/scripts/wait_job.sh JOBID 540 PATH/TO/progress_file

The helper prints one status line and exits with:
- 0 when the job has reached a final state (State, ExitCode, Elapsed and node);
- 3 when the job is still queued or running at the limit, so another wait
  continues it;
- 4 when the job has ended but the site kept no record of how: it has no Slurm
  accounting and the controller has forgotten the job. Its output files and log
  are the only evidence of how it ended;
- 2 for a malformed or unknown job id.

The record comes from `sacct`. On a site without accounting, or before `sacct`
has the job, it comes from `scontrol`, which holds a job for a few minutes after
it ends. A job counts as finished only when one of them reports a final state,
or when the controller says it no longer knows a job the helper saw before, so a
transient `squeue` or controller failure cannot end the wait early. On a site
where `sacct` says accounting is disabled, calling it returns nothing useful.

## Waiting

- A wait longer than the tool timeout (540 s unless the runtime states a longer
  one), or than the turn's no-progress watchdog, ends with its outcome unknown,
  and track of the job is lost.
- Each poll costs a model step; polling every few seconds spends them for
  nothing, and narration around a wait adds nothing either.
- While a long job runs, work that does not depend on it (delivery commands,
  summary sections) can be prepared. The program's skill's bundled checks
  already cover verification.

## After the job ends

- The expected output files show whether it produced what it should.
- A failed job's stdout and stderr hold the cause; a resubmission without a
  stated cause repeats the failure.
- Every job id submitted, including cancelled ones with the reason, is part of
  the record.
