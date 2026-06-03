---
name: coordinate_two_version_hpc_regression
title: Coordinate Two-Version HPC Regression
description: Coordinate baseline/candidate HPC I/O regression analysis through child experts.
---

When the user asks for an HPC I/O regression comparison, preserve the baseline
and candidate paths exactly and delegate bounded work instead of answering from
memory.

The expected route is: ingest the traces, compare aligned metrics, ask for root
cause attribution, then synthesize the final answer. The final answer should
separate stable evidence from regressed evidence and cite the metric changes
that support the root-cause hypothesis.
