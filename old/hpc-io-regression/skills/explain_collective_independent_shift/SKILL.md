---
name: explain_collective_independent_shift
title: Explain Collective Independent Shift
description: Explain performance impact from collective to independent I/O shifts.
---

When collective writes decrease and independent writes increase, explain that
the candidate may be issuing less coordinated I/O. This can fragment accesses,
increase POSIX write time, and raise metadata overhead even when total bytes
are unchanged.

Tie the explanation to the observed collective and independent write counts.
Do not claim this cause if those counts are absent or unchanged.
