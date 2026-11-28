---
name: treatment-response
title: Treatment Response
description: Use for questions comparing treatments or genotypes in a phenotyping experiment (dose-response, genotype x treatment interaction, replicates, position effects).
keywords:
- level:L1
- phenotyping
- statistics
---

# Treatment response

## The design decides the model, not the question

- **What the treatment is.** The source design information and any relevant
  saved findings say; a design view or card is optional. A numeric dose with a
  confirmed unit supports dose-response; a category (control vs treated, named
  agents) supports contrasts only. When the card lists the treatment's meaning as
  an open question, its levels are unordered categories, and that choice is part
  of the result.
- **The unit of replication.** Usually the plant/pot. Several images of the same
  plant are repeated measures, not replicates. Replicates per cell come from the
  actual unit and factor mappings.
- **What else structures the data.** Genotype, tray/position, block, session.
  With treatments mixed within trays, position can be a covariate or random
  effect; with trays confounded with treatment, the effects cannot be separated.

## Methods

- **Categorical treatments**: per genotype and overall; with replicates per cell,
  a two-way model (genotype, treatment, and their interaction); effect sizes with
  intervals say more than p-values alone.
- **Doses**: a response curve per genotype (log-logistic for inhibition, or a
  monotone spline) needs enough levels; EC-style summaries are meaningful only
  when the curve is identifiable within the tested range. With few levels, doses
  are ordered categories with a trend test.
- **Genotype x treatment**: the interaction is the test; genotypes rank by
  response (difference or ratio to their own control), not by raw means.
- **Repeated measures**: each unit's trajectory summarised (area under curve,
  final unclipped value, growth rate -- see `size-and-growth-traits`) and the
  summaries compared, or a mixed model with unit as a random effect. Pooling all
  sessions as if independent inflates n.
- **Multiple testing**: correction across genotypes/traits (for example
  Benjamini-Hochberg) changes which effects stand, and readers need to know it
  was applied.
- **Unbalanced cells**: models that handle imbalance (type II/III sums of
  squares, mixed models), with the cell counts visible.

## What a treatment result rests on

- Outliers and suspicious scales investigated, with any justified analytical
  exclusions and affected counts stated; the original source values preserved.
- Units and relative vs absolute scales stated; relative units (a.u.) are not
  compared across instruments.
- Every number from computed output (script or tool), with the model and the
  sample size.
