---
name: align_hpc_trace_metrics
title: Align HPC Trace Metrics
description: Align parsed baseline and candidate Darshan metrics before ranking deltas.
---

Compare only metrics that are present on both sides unless the absence itself
is the evidence. Normalize field names before comparing, and keep units visible
in the response.

Important aligned metrics include runtime, POSIX read/write bytes, POSIX
read/write time, POSIX metadata time, MPI-IO collective writes, MPI-IO
independent writes, and transfer-size hints.
