---
name: hpc-batch-jobs
title: Run and Wait on Slurm Batch Jobs Safely
description: Submit Slurm jobs, record their ids, and wait on them in bounded, low-output steps so no single tool call outlives the tool timeout or the turn's no-progress watchdog.
---

Submit with `sbatch --parsable`. Record the job id at once in the workspace (for example
`jobs/job_ids.txt`), together with the submit time and the script path.

Wait in bounded steps with the bundled helper. `SKILL_ROOT` is the skill directory reported by `load_skill`:

    bash SKILL_ROOT/scripts/wait_job.sh JOBID 540 PATH/TO/progress_file

The helper prints one status line and exits with:
- 0 when the job has reached a final state (State, ExitCode, Elapsed and node from `sacct`);
- 3 when the job is still queued or running at the limit. Call it again in the next step;
- 2 for a malformed or unknown job id.

Rules for wait steps:
- Keep each wait at or below 540 s unless the runtime states a longer tool timeout. A call that outlives the tool
  timeout or the turn's no-progress watchdog ends with its outcome unknown, and you lose track of the job.
- A wait step needs no narration. Issue the next wait call with at most one short sentence.
- Do not poll every few seconds: each poll costs a model step.
- While a long job runs, use the first wait steps to prepare the remaining non-dependent work, such as delivery
  commands or summary sections. Do not write new verification programs; use the bundled checks of the relevant
  skill, for example `morphorm`.

After the job ends:
- Check the expected output files.
- On failure, read the job's stdout and stderr before you change anything, and resubmit only with a stated cause.
- Report every job id you submitted, including cancelled ones, with the reason.
