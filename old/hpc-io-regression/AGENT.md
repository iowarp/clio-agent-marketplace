---
id: hpc-io-regression
title: HPC I/O Regression Agent
version: 0.1.0
description: Compares HPC I/O traces across two application versions and attributes performance regressions.
root_expert: main
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/main.md
  - experts/trace_ingest.md
  - experts/baseline_ingest.md
  - experts/candidate_ingest.md
  - experts/regression_diff.md
  - experts/root_cause.md
defaults:
  prompt_profile: heavy
---

# HPC I/O Regression Agent

A domain agent for paired HPC performance traces, Darshan text reports, and
I/O-regression triage. It parses baseline and candidate traces through bounded
ingest children, aligns metrics, ranks changed I/O behavior, and returns a
root-cause hypothesis with caveats for partial or incomparable traces.
