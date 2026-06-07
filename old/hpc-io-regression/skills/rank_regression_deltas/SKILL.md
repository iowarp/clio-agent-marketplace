---
name: rank_regression_deltas
title: Rank Regression Deltas
description: Rank I/O metric deltas by likely performance impact.
---

Rank deltas by performance relevance, not by textual order. Large increases in
write time, metadata time, runtime, independent writes, or small transfer-size
behavior are usually more important than unchanged byte counts.

Report absolute values and direction for the highest-impact changes. Make clear
when a metric is stable so the user can distinguish cause from coincidence.
