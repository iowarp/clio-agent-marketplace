---
name: darshan_text_parsing
title: Darshan Text Parsing
description: Parse Darshan-style text exports into normalized I/O metrics.
---

Use the Darshan parsing tool for any trace file path before summarizing metrics.
Preserve parser warnings, missing counters, and the source path.

Important fields include runtime, nprocs, POSIX byte counters, POSIX read/write
and metadata times, MPI-IO collective and independent write counters, and
transfer-size hints. If a metric is absent, report the absence instead of
inventing a value.
