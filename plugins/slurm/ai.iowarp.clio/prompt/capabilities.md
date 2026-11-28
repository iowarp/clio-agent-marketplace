---
id: slurm.capabilities
section: capabilities
when: {"tools": ["shell_bash"]}
---

On a Slurm cluster, `hpc-batch-jobs` covers batch work from the first `sbatch`:
recording job ids, waiting in bounded steps with a bundled helper, and reading a
failed job's output before any resubmission. Whether a cluster is reachable, and
with which account and partition, is something to check or ask about; it is not
known in advance.
