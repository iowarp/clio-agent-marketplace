---
id: genomics-review
title: Genomics Review Agent
version: 0.1.0
description: Reviews small reference FASTA and VCF variant files for collaborator handoff.
root_expert: main
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/main.md
  - experts/reference.md
  - experts/reference_quality.md
  - experts/variants.md
  - experts/variant_impact.md
  - experts/cohort_qc.md
defaults:
  prompt_profile: heavy
---

# Genomics Review Agent

A domain agent for small genomics handoff reviews. It separates reference
inspection, reference quality, variant review, variant impact triage, and
cohort-level sample QC so CLIO can test per-session agent activation with a
hierarchy that is not the default data-exploration agent.
