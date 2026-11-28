---
name: xct
title: Characterize Internal Defects and Porosity With X-Ray Computed Tomography
description: Use when interpreting XCT pore and defect statistics - what acquisition and segmentation allow, porosity by formation mechanism, and size and location distributions.
keywords:
- level:L1
- characterization
- xct
- porosity
---

## Acquisition

A scan is defined by its acquisition conditions: voxel size, source and detector
geometry (cone beam or other), energy and filtering, and the known artifacts: beam
hardening, rings, scatter, and streaking in dense or high-atomic-number
material. Voxel size sets a hard floor on the smallest feature that is
reliably detected; a pore near or below that size is not reliably sized or
counted.

## Segmentation is a modelling choice

The threshold or segmentation method, and how it was validated (a
calibration phantom, an independent technique, a held-out labelled region),
shape every statistic. Pore volume fraction, count and size distribution move
under plausible threshold changes: partial-volume blur at boundaries
routinely biases size and count. The segmentation script and its parameters
are what make the results reproducible.

## Classify porosity by mechanism

Porosity has formation mechanisms that a single number hides:

- gas porosity: typically near-spherical, from dissolved or entrapped gas;
- keyhole porosity, in fusion processes: from vapour-cavity collapse;
- lack-of-fusion porosity: irregular, elongated, often with unmelted powder,
  from insufficient energy input or overlap.

Each implies a different process cause (`am-process-parameters`) and a
different fatigue severity at the same volume fraction.

## Distributions, not averages

The size distribution and spatial location of the defects, with the
largest features and their distance to free surfaces, say more than the
average: fatigue assessments (`defect-driven-fatigue`) need the worst
individual defects near high-stress regions, not average porosity. A
porosity number is only as trustworthy as the smallest pore the method could
detect; a 2D section estimate (`microstructure`) carries section bias instead
of a voxel floor. `defect-characterization` and `defect-driven-fatigue` build on
these results.
