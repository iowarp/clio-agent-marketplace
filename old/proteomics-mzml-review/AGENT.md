---
id: proteomics-mzml-review
title: Proteomics Review Agent
version: 0.2.0
description: Reviews mzML runs and LFQ protein-intensity matrices for proteomics handoff readiness.
root_expert: main
blueprint:
  format: agent-blueprint-v1
experts:
  - experts/main.md
  - experts/mass_spec.md
  - experts/spectra_quality.md
  - experts/search_readiness.md
  - experts/lfq_differential.md
defaults:
  prompt_profile: heavy
---

# Proteomics Review Agent

A proteomics-domain agent for raw mzML inspection, MS-level balance, spectra
quality, m/z coverage, TIC evidence, peptide-search readiness checks, and LFQ
protein differential-abundance review from MaxQuant-style intensity matrices.
