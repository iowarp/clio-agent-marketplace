---
name: separate_stable_from_regressed_metrics
title: Separate Stable From Regressed Metrics
description: Separate unchanged workload evidence from regressed I/O behavior.
---

In the comparison result, explicitly group stable metrics apart from regressed
metrics. Stable rank count and byte volumes are evidence that the slowdown is
not explained by a larger workload.

Use stable metrics to constrain the root-cause explanation. Do not attribute a
slowdown to increased data volume if read/write byte counts are unchanged.
