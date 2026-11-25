---
name: hpc-batch-jobs
title: Run and Wait on Slurm Batch Jobs Safely
description: Use to submit Slurm jobs and wait on them in bounded, low-output steps, reporting every job id.
keywords:
- level:L2
- slurm
- hpc
---

Submit with `sbatch --parsable`. Record the job id at once in the workspace
(for example `jobs/job_ids.txt`), together with the submit time and the
script path.

This skill is for jobs you submit yourself on the machine CLIO runs on. A job on
a remote site, such as a cluster reached over SSH, goes through relay
(`clio-relay`'s `run`, `install` or `exec`), never through `ssh` in a shell. A
job that relay's `run` or `serve` started is waited on through relay (its task,
or `serve`'s `until="steps"`), never with this helper or `sacct`.

Wait in bounded steps with the bundled helper. `SKILL_ROOT` is the skill
directory reported by `load_skill`:

    bash SKILL_ROOT/scripts/wait_job.sh JOBID 540 PATH/TO/progress_file

The helper prints one status line and exits with:
- 0 when the job has reached a final state (State, ExitCode, Elapsed and node);
- 3 when the job is still queued or running at the limit. Call it again in the
  next step;
- 4 when the job has ended but the site kept no record of how: it has no Slurm
  accounting and the controller has forgotten the job. Judge it by its output
  files and log;
- 2 for a malformed or unknown job id.

The record comes from `sacct`. On a site without accounting, or before `sacct`
has the job, it comes from `scontrol`, which holds a job for a few minutes after
it ends. A job counts as finished only when one of them reports a final state,
or when the controller says it no longer knows a job the helper saw before, so a
transient `squeue` or controller failure cannot end the wait early. Do not call
`sacct` yourself on a site where it says accounting is disabled.

Rules for wait steps:
- Keep each wait at or below 540 s unless the runtime states a longer tool
  timeout. A call that outlives the tool timeout or the turn's no-progress
  watchdog ends with its outcome unknown, and you lose track of the job.
- A wait step needs no narration. Issue the next wait call with at most one
  short sentence.
- Do not poll every few seconds: each poll costs a model step.
- While a long job runs, use the first wait steps to prepare the remaining
  work that does not depend on it, such as delivery commands or summary
  sections. Verify with the bundled checks of the program's skill rather than
  writing new verification programs.

After the job ends:
- Check the expected output files.
- On failure, read the job's stdout and stderr before you change anything,
  and resubmit only with a stated cause.
- Report every job id you submitted, including cancelled ones, with the
  reason.
