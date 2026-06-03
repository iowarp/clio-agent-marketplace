---
name: parse_one_baseline_trace
title: Parse One Baseline Trace
description: Parse one baseline Darshan-style trace and preserve evidence for later comparison.
---

Use this skill when the expert is responsible for the baseline side of an
HPC I/O regression comparison.

Always parse the baseline trace with the assigned tool before making claims.
Return a compact evidence block containing the original path, runtime, rank
count, read/write byte totals, read/write timing, metadata timing, collective
and independent write counts, transfer-size hints, and any parser warnings.

Do not compare against the candidate trace in this expert. Return the normalized
baseline metrics to the parent so the parent can merge both sides.
