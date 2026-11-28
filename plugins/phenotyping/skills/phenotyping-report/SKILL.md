---
name: phenotyping-report
title: Phenotyping Report
description: Use when the user asks for a report, summary or write-up of a phenotyping analysis.
keywords:
- level:L1
- phenotyping
- report
---

# Phenotyping report

A report combines inspected source evidence and computed results. A card can
help when present; it is not a prerequisite. Facts unsupported by the inspected
files, recorded user answers or tool output do not belong in it.

## What a phenotyping report carries

- The question, the main result with its effect size and uncertainty, and the
  most important caveat.
- The experiment as the source states it: identity and any version, relevant
  input fingerprints, species, observed design (factors, levels, replicates,
  balance), period and sessions used. Missing metadata is a gap to name, not
  something to invent or a reason to require a card.
- Sensors and traits used (trait / method / scale), the traps found and how each
  was handled, exclusions with counts.
- Aggregation over sessions, models and tests, software, analysis-code or query
  references and relevant input/output fingerprints. A fixed loader or
  materialized views are not required.
- Tables and figures, each with n, units, and uncertainty; what was observed,
  calculated and interpreted, in ordinary language, with clickable supporting
  references near the claim (see `evidence-and-claims`).
- What the analysis assumed, and the questions for the data owners that would
  change the result.

## Facts that hold in any report

- Numbers come from computed output, traceable to the script or tool call.
- Relative units stay relative; arbitrary units do not convert to physical ones.
- Biology the data does not show (gene function, mechanisms) is external context
  unless the user supplied it.
- Generic chart presets fit phenotyping figures (trajectories per unit, box plots
  per group, heatmaps of genotype x treatment), with their data registered as
  artifacts.
- A Markdown artifact is the default format: `create_artifact` with a
  workspace-relative `.md` name, `kind="report"`, the complete Markdown as
  `content`, and `used` listing the actual source references and derived files.
  It returns the artifact id and version; until creation succeeds the report does
  not exist.
