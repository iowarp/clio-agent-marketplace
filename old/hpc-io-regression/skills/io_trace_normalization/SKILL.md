---
name: io_trace_normalization
title: I/O Trace Normalization
description: Normalize parsed HPC trace counters into comparable summaries.
---

Normalize names and units so parent experts can compare traces without
re-parsing raw text. Keep seconds as seconds and byte counts as bytes unless
the final answer explicitly chooses human-readable units.

Include a compact phase summary for write time, read time, metadata time,
write bytes, read bytes, write operation counts, and collective write fraction
when enough fields are available.
