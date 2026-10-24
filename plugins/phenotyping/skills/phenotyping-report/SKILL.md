---
name: phenotyping-report
title: Phenotyping Report
description: Structure a phenotyping analysis report with evidence and caveats - experiment identity, design, data quality, methods, results with specific supporting references, and open questions. Use when the user asks for a report, summary, or write-up of a phenotyping analysis.
keywords:
- level:L1
- phenotyping
- report
---

# Phenotyping report

A report combines inspected source evidence and computed results. A card can
help when present; it is not a prerequisite. Do not add facts unsupported by
the inspected files, recorded user answers or tool output.

## Structure

1. **Summary** (3-5 sentences): the question, the main result with its effect
   size and uncertainty, and the most important caveat.
2. **Experiment**: identity and any version actually stated by the source,
   relevant input fingerprints, species, observed design (factors, levels,
   replicates, balance), period and sessions used. Identify missing metadata
   rather than inventing it or requiring a card.
3. **Data and quality**: sensors and traits used (trait / method / scale),
   the traps found and how each was handled, exclusions with counts.
4. **Methods**: aggregation over sessions, models and tests, software and
   analysis-code or query references and relevant input/output fingerprints.
   A fixed loader or materialized views are not required.
5. **Results**: tables and figures, each with n, units, and uncertainty.
   Explain what was observed, calculated and interpreted in ordinary language,
   with clickable supporting references near the claim (see `evidence-and-claims`).
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
- Deliver as a Markdown artifact unless the user asks for another format:
  call `create_artifact` with a workspace-relative `.md` name, `kind="report"`,
  the complete Markdown as `content`, and `used` listing the actual source
  references and derived files it uses. Keep the returned artifact id and
  version, and only say the report exists once creation succeeded.
