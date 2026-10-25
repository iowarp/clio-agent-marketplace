#!/usr/bin/env bash
# Bounded wait on one Slurm job; prints ONE compact status line, so a wait step costs almost no output.
# Usage: wait_job.sh JOBID [MAX_SECONDS=540] [PROGRESS_FILE] [POLL_SECONDS=30]
#   Waits until the job has reached a final state or MAX_SECONDS pass (keep MAX_SECONDS under the tool timeout).
#   Exit 0 = job finished (prints sacct State/ExitCode/Elapsed), 3 = still queued/running at the limit (call again),
#   2 = usage error or a job id that neither squeue nor sacct knows. With PROGRESS_FILE, the line also shows that file's line count and its last line.
#   A job counts as finished only when sacct reports a final state, so a transient squeue failure cannot end the wait.
jid=${1:?usage: wait_job.sh JOBID [MAX_SECONDS] [PROGRESS_FILE] [POLL_SECONDS]}
max=${2:-540}; prog=${3:-}; poll=${4:-30}
[[ "$jid" =~ ^[0-9]+$ ]] || { echo "wait_job: bad job id '$jid'" >&2; exit 2; }
state(){ sacct -X -n -P -j "$jid" -o State 2>/dev/null | head -1 | cut -d'|' -f1 | awk '{print $1}'; }
final(){ case "$(state)" in COMPLETED|FAILED|CANCELLED|TIMEOUT|OUT_OF_MEMORY|NODE_FAIL|PREEMPTED|BOOT_FAIL|DEADLINE) return 0;; esac; return 1; }
if ! squeue -h -j "$jid" 2>/dev/null | grep -q . && [[ -z "$(state)" ]]; then echo "wait_job: unknown job id $jid" >&2; exit 2; fi
end=$((SECONDS + max))
until final || (( SECONDS >= end )); do sleep "$poll"; done
p=""
if [[ -n "$prog" && -f "$prog" ]]; then p=" | $(wc -l < "$prog") lines in $(basename "$prog"); last: $(grep -v '^[[:space:]]*$' "$prog" | tail -n 1 | tr -s ' ' | cut -c1-120)"; fi
if final; then
  echo "$(date -u +%FT%TZ) job $jid finished: $(sacct -X -n -P -j "$jid" -o State,ExitCode,Elapsed,NodeList 2>/dev/null | head -1)$p"
  exit 0
fi
echo "$(date -u +%FT%TZ) job $jid $(squeue -h -j "$jid" -o '%T elapsed=%M node=%N' 2>/dev/null | head -1) state=$(state)$p"
exit 3
