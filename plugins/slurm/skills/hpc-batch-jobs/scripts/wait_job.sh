#!/usr/bin/env bash
# Bounded wait on one Slurm job; prints ONE compact status line, so a wait step costs almost no output.
# Usage: wait_job.sh JOBID [MAX_SECONDS=540] [PROGRESS_FILE] [POLL_SECONDS=30]
#   Waits until the job has reached a final state or MAX_SECONDS pass (keep MAX_SECONDS under the tool timeout).
#   Exit 0 = job finished (prints State|ExitCode|Elapsed|NodeList), 3 = still queued/running at the limit (call again),
#   4 = the job ended but the site kept no record of how (no Slurm accounting, and the controller has forgotten it),
#   2 = usage error or a job id that neither sacct, scontrol nor squeue knows.
#   With PROGRESS_FILE, the line also shows that file's line count and its last line.
#   The job's record comes from sacct; where sacct has none (accounting off, or not yet written) it comes from
#   scontrol, which holds a job for a few minutes after it ends. A job counts as finished only when one of them
#   reports a final state, or when the controller says it no longer knows a job this helper saw before on a site
#   without accounting, so a transient squeue or controller failure cannot end the wait.
jid=${1:?usage: wait_job.sh JOBID [MAX_SECONDS] [PROGRESS_FILE] [POLL_SECONDS]}
max=${2:-540}; prog=${3:-}; poll=${4:-30}
[[ "$jid" =~ ^[0-9]+$ ]] || { echo "wait_job: bad job id '$jid'" >&2; exit 2; }
finals='COMPLETED|FAILED|CANCELLED|TIMEOUT|OUT_OF_MEMORY|NODE_FAIL|PREEMPTED|BOOT_FAIL|DEADLINE'
acct=1
if sacct -n -X -j "$jid" -o JobID 2>&1 >/dev/null | grep -qi 'accounting storage is disabled'; then acct=0; fi
seen_dir="${TMPDIR:-/tmp}/wait_job-$(id -u)"
find "$seen_dir" -type f -mtime +7 -delete 2>/dev/null
mark(){ mkdir -p "$seen_dir" 2>/dev/null && : > "$seen_dir/$jid" 2>/dev/null; }
marked(){ [[ -e "$seen_dir/$jid" ]]; }
field(){ grep -oE "(^| )$1=[^ ]*" <<<"$2" | head -1 | sed -E "s/^ ?$1=//"; }
# Sets st (the state's first word), rec (State|ExitCode|Elapsed|NodeList) and gone (the controller said it no
# longer knows the job).
look(){
  st=""; rec=""; gone=0
  if (( acct )); then
    rec=$(sacct -X -n -P -j "$jid" -o State,ExitCode,Elapsed,NodeList 2>/dev/null | head -1)
    st=$(cut -d'|' -f1 <<<"$rec" | awk '{print $1}')
  fi
  if [[ -z "$st" ]]; then
    local out line
    out=$(scontrol show job -o "$jid" 2>&1)
    if grep -qi 'invalid job id' <<<"$out"; then
      gone=1
    else
      line=$(grep -m1 'JobState=' <<<"$out")
      if [[ -n "$line" ]]; then
        st=$(field JobState "$line")
        rec="$st|$(field ExitCode "$line")|$(field RunTime "$line")|$(field NodeList "$line")"
      fi
    fi
  fi
  if [[ -n "$st" ]]; then mark; fi
}
final(){ [[ "$st" =~ ^($finals)$ ]]; }
forgotten(){ (( gone && ! acct )) && marked; }
look
queued=$(squeue -h -j "$jid" 2>/dev/null | head -1)
if [[ -n "$queued" ]]; then mark; fi
if [[ -z "$st" && -z "$queued" ]] && ! forgotten; then
  why=""
  (( acct )) || why=" (this site keeps no Slurm accounting, so a job that ended more than a few minutes ago is forgotten too: judge such a job by its output)"
  echo "wait_job: unknown job id $jid$why" >&2; exit 2
fi
end=$((SECONDS + max))
until final || forgotten || (( SECONDS >= end )); do sleep "$poll"; look; done
p=""
if [[ -n "$prog" && -f "$prog" ]]; then p=" | $(wc -l < "$prog") lines in $(basename "$prog"); last: $(grep -v '^[[:space:]]*$' "$prog" | tail -n 1 | tr -s ' ' | cut -c1-120)"; fi
if final; then
  echo "$(date -u +%FT%TZ) job $jid finished: $rec$p"
  exit 0
fi
if forgotten; then
  echo "$(date -u +%FT%TZ) job $jid ended: the controller no longer holds it and this site keeps no Slurm accounting, so how it ended is unknown; judge it by its output$p"
  exit 4
fi
echo "$(date -u +%FT%TZ) job $jid $(squeue -h -j "$jid" -o '%T elapsed=%M node=%N' 2>/dev/null | head -1) state=$st$p"
exit 3