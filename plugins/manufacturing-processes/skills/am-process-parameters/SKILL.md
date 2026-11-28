---
name: am-process-parameters
title: Record AM Process Parameters and Trace Them to Melt-Pool Regime and Defects
description: Use when relating additive manufacturing process parameters to part quality, including laser powder bed fusion melt-pool regimes, defects and texture.
keywords:
- level:L1
- additive-manufacturing
- process-parameters
---

## The full set

The parameters that control each process family:

- **Powder bed fusion (laser or electron beam)**: beam power, scan speed,
  hatch spacing, layer thickness, spot size, scan strategy (stripes, islands,
  rotation between layers, contour passes), preheat or chamber temperature,
  atmosphere and oxygen level, powder lot and reuse count.
- **Directed energy deposition**: power, travel speed, feed rate of powder or
  wire, deposition path, interpass temperature or dwell.
- Other families: the controlling parameters their own standards and machine
  documentation name.

A derived metric such as volumetric energy density discards information: the
same value can come from different power and speed combinations with
different melt-pool behaviour, so it means little without the parameters.

## Qualification and provenance

- Parameters are either validated for this material, machine and powder lot, or
  assumed from a similar system. A set tuned on one
  machine, lot or alloy does not transfer without requalification:
  absorptivity, thermal conductivity and melting range differ by material.
- Nominal (programmed) values differ from verified (measured or logged)
  ones. Actual power, layer thickness and oxygen level drift from the
  programme; a defect investigation checks which values the build used.

## Laser powder bed fusion: regime and defects

A parameter set produces a melt-pool regime (conduction, keyhole,
lack-of-fusion prone), and the regime implies a defect mechanism through
melt-pool physics, not a correlation alone:

- keyhole mode produces keyhole porosity from vapour-cavity collapse;
- insufficient energy input or overlap produces irregular lack-of-fusion
  porosity, often with unmelted powder;
- spatter and denudation affect surface quality and can seed near-surface
  defects;
- powder reuse and oxygen content shift the defect population.

Scan strategy sets residual stress and the direction of columnar grain growth
relative to the build axis; `build-orientation` covers the resulting
anisotropy. A predicted defect population is a prediction until measurement
(`xct`, `fractography`) confirms it.
