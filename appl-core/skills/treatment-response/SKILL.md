---
name: treatment-response
title: Treatment Response
description: DRAFT. Analyse how traits respond to treatments in a phenotyping experiment - dose-response vs categorical contrasts, genotype x treatment interaction, replicates, repeated measures, and tray/position effects. Use for questions comparing treatments or genotypes.
keywords:
- level:L1
- phenotyping
- statistics
---

# Treatment response (draft)

## Decide the model from the design, not from the question

1. **What is the treatment?** Read the design view and the card. A numeric
   dose with a confirmed unit supports dose-response; a category (control vs
   treated, named agents) supports contrasts only. If the card lists the
   treatment's meaning as an open question, say the analysis treats levels as
   unordered categories and why.
2. **What is the unit of replication?** Usually the plant/pot. Several images
   of the same plant are repeated measures, not replicates. Count replicates
   per cell from `design`.
3. **What else structures the data?** Genotype, tray/position, block, session.
   If treatments are mixed within trays, position can be a covariate or random
   effect; if trays are confounded with treatment, say that effects cannot be
   separated.

## Methods

- **Categorical treatments**: compare per genotype and overall; with
  replicates per cell, use a two-way model (genotype, treatment, and their
  interaction); report effect sizes with intervals, not only p-values.
- **Doses**: fit a response curve per genotype (log-logistic for
  inhibition, or a monotone spline) when there are enough levels; report
  EC-style summaries only when the curve is identifiable within the tested
  range. With few levels, treat doses as ordered categories and test a trend.
- **Genotype x treatment**: test the interaction; rank genotypes by response
  (difference or ratio to their own control), not by raw means.
- **Repeated measures**: summarise each unit's trajectory first (area under
  curve, final unclipped value, growth rate -- see `size-and-growth-traits`),
  then compare the summaries; or fit a mixed model with unit as a random
  effect. Never pool all sessions as if independent.
- **Multiple testing**: correct across genotypes/traits (for example
  Benjamini-Hochberg) and say so.
- **Unbalanced cells**: use models that handle imbalance (type II/III sums of
  squares, mixed models); report the cell counts.

## Checks before reporting

- Outliers and scale errors removed per the card, with counts.
- Units and relative vs absolute scales stated; relative units (a.u.) are not
  compared across instruments.
- Every number comes from computed output (script or tool), with the model
  and the sample size.
