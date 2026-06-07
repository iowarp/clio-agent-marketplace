---
id: genomics-review
title: Genomics Review Agent
version: 0.1.0
description: Coordinates cohort QC, reference review, and VCF variant handoff for small genomics studies.
root_expert: main
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/main.md
  - experts/cohort_qc.md
  - experts/per_sample_metrics.md
  - experts/cohort_outliers.md
  - experts/manifest_reconciliation.md
  - experts/reference.md
  - experts/reference_quality.md
  - experts/variants.md
  - experts/variant_impact.md
defaults:
  prompt_profile: heavy
---

# Genomics Review Agent

A domain agent for genomics cohort handoff review. Its primary benchmark path
is cohort QC: per-sample genotype metrics, cohort-level outlier interpretation,
and manifest reconciliation when manifest evidence is available. It also keeps
secondary reference FASTA and VCF variant-review paths so the same domain agent
can support collaborator handoff questions without swapping packs.

The cohort path follows the researched CLIO benchmark semantics: the root
delegates to a cohort parent expert, that expert gathers bounded per-sample
metrics, merges cohort outlier evidence, asks a manifest reconciliation expert
to cross-check available metadata, then returns a compact drop/keep advisory.
