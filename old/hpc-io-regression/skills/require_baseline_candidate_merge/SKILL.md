---
name: require_baseline_candidate_merge
title: Require Baseline Candidate Merge
description: Require both sides of a paired trace comparison before final synthesis.
---

Do not finalize a two-version I/O regression answer until the baseline and
candidate evidence have either both returned or one side has returned a
structured partial failure.

If one side is missing, corrupt, or unparseable, report the partial failure and
state which comparison claims are unsupported. If both sides are available,
merge on shared metrics: runtime, bytes, timing, operations, metadata overhead,
and collective versus independent behavior.
