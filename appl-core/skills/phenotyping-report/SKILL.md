---
name: phenotyping-report
title: Phenotyping Report
description: DRAFT. Structure a phenotyping analysis report with evidence and caveats - experiment identity, design, data quality, methods, results with tagged claims, and open questions. Use when the user asks for a report, summary, or write-up of a phenotyping analysis.
keywords:
- level:L1
- phenotyping
- report
---

# Phenotyping report (draft)

A report is a view of the experiment card plus computed results. It adds no
facts that are not in the card or in tool output from this work.

## Structure

1. **Summary** (3-5 sentences): the question, the main result with its effect
   size and uncertainty, and the most important caveat.
2. **Experiment**: identity from the card (dataset name and version as the
   export states them, manifest hash), species, design (factors, levels,
   replicates, balance table), period and sessions used.
3. **Data and quality**: sensors and traits used (trait / method / scale),
   the traps found and how each was handled, exclusions with counts.
4. **Methods**: aggregation over sessions, models and tests, software and
   loader path, view hashes.
5. **Results**: tables and figures, each with n, units, and uncertainty.
   Every claim tagged `[stated]`, `[checked]`, or `[inferred]` (see
   `evidence-and-claims`).
6. **Caveats and open questions**: what the analysis assumed, and the
   questions for the data owners that would change the result.

## Rules

- Numbers come from computed output; cite the script or tool call.
- Relative units stay relative; do not convert arbitrary units to physical
  ones.
- Do not interpret biology the data does not show (gene function, mechanisms)
  unless the user supplied it; mark any such context as external.
- Figures use generic chart presets (trajectories per unit, box plots per
  group, heatmaps of genotype x treatment) and register their data as
  artifacts.
- Deliver as a Markdown artifact unless the user asks for another format.
