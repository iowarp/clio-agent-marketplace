---
name: partial_trace_caveats
title: Partial Trace Caveats
description: Preserve caveats for missing, truncated, or incomplete HPC trace evidence.
---

If a trace cannot be parsed completely, return a structured partial result
instead of hiding the problem. Include the path, the missing fields, parser
warnings, and which downstream comparisons are still valid.

Partial evidence can still be useful, but the final answer must not overstate
unsupported comparisons.
