---
name: parse_one_candidate_trace
title: Parse One Candidate Trace
description: Parse one candidate Darshan-style trace and preserve evidence for later comparison.
---

Use this skill when the expert is responsible for the candidate side of an
HPC I/O regression comparison.

Always parse the candidate trace with the assigned tool before making claims.
Return a compact evidence block containing the original path, runtime, rank
count, read/write byte totals, read/write timing, metadata timing, collective
and independent write counts, transfer-size hints, and any parser warnings.

Do not decide root cause in this expert. Return normalized candidate metrics to
the parent so comparison and attribution happen after both branches return.
