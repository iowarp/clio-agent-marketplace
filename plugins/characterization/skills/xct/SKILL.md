---
name: xct
title: Characterize Internal Defects and Porosity With X-Ray Computed Tomography
description: Connect XCT acquisition and segmentation choices to what the resulting pore and defect statistics can support, classify porosity by formation mechanism, and report size and location distributions rather than one volume fraction.
keywords:
- level:L1
- characterization
- xct
- porosity
---

## Acquisition

Record the acquisition conditions: voxel size, source and detector geometry
(cone beam or other), energy and filtering, and the known artifacts: beam
hardening, rings, scatter, and streaking in dense or high-atomic-number
material. Voxel size sets a hard floor on the smallest feature that is
reliably detected; a pore near or below that size is not reliably sized or
counted.

## Segmentation is a modelling choice

State the threshold or segmentation method and how it was validated (a
calibration phantom, an independent technique, a held-out labelled region).
Report how the statistics (pore volume fraction, count, size distribution)
change under plausible threshold changes: partial-volume blur at boundaries
routinely biases size and count. Keep the segmentation script and its
parameters with the results.

## Classify porosity by mechanism

Report porosity by formation mechanism before giving any single number:

- gas porosity: typically near-spherical, from dissolved or entrapped gas;
- keyhole porosity, in fusion processes: from vapour-cavity collapse;
- lack-of-fusion porosity: irregular, elongated, often with unmelted powder,
  from insufficient energy input or overlap.

Each implies a different process cause (`am-process-parameters`) and a
different fatigue severity at the same volume fraction.

## Report distributions, not averages

Report the size distribution and spatial location of the defects, with the
largest features and their distance to free surfaces listed separately from
the average: fatigue assessments (`defect-driven-fatigue`) need the worst
individual defects near high-stress regions, not average porosity. A
porosity number is only as trustworthy as the smallest pore the method could
detect; a 2D section estimate (`microstructure`) carries section bias instead
of a voxel floor.

## Return

The acquisition conditions and artifacts, the segmentation method and its
sensitivity, the porosity classified by mechanism, and the size and location
distribution with the largest defects stated separately, for
`defect-characterization` or `defect-driven-fatigue`.
