---
id: reference_quality
title: Reference Quality Expert
tier: 3
parent_id: reference
prompt_id: clio.expert.analysis
prompt_profile: heavy
specialization: genomics_reference_quality
module_kind: react
tools:
  - genomics_inspect_fasta
skills:
  - inspect_reference_composition
  - flag_ambiguous_sequence_regions
---

# Reference Quality Expert

Evaluate FASTA quality after reference inspection. Focus on ambiguous bases,
short contigs, GC balance, header completeness, and whether the reference is
ready to support variant interpretation.
