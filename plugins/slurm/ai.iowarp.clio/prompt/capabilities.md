---
id: slurm.capabilities
section: capabilities
when: {"tools": ["shell_bash"]}
---
When work runs on a Slurm cluster, load `hpc-batch-jobs` before the first
`sbatch`: it records job ids, waits in bounded steps with a bundled helper,
and reads a failed job's output before any resubmission. Whether a cluster is
reachable, and with which account and partition, is checked or asked, not
assumed.
