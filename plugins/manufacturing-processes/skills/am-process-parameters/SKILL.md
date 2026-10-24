---
name: am-process-parameters
title: Record AM Process Parameters and Trace Them to Melt-Pool Regime and Defects
description: Treat the complete additive process parameter set, not one energy-density number, as what determines part quality; record nominal versus verified values and qualification, and for laser powder bed fusion trace parameters to melt-pool regime, defect mechanism and texture.
keywords:
- level:L1
- additive-manufacturing
- process-parameters
---

## Record the full set

Record every parameter that controls the process family:

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
different melt-pool behaviour. Report it only alongside the parameters.

## Qualification and provenance

- State which parameters were validated for this material, machine and powder
  lot, and which were assumed from a similar system. A set tuned on one
  machine, lot or alloy does not transfer without requalification:
  absorptivity, thermal conductivity and melting range differ by material.
- Distinguish nominal (programmed) values from verified (measured or logged)
  ones. Actual power, layer thickness and oxygen level drift from the
  programme; a defect investigation checks which values the build used.

## Laser powder bed fusion: regime and defects

Name the melt-pool regime the parameter set produces (conduction, keyhole,
lack-of-fusion prone) and the defect mechanism it implies, from melt-pool
physics rather than a correlation alone:

- keyhole mode produces keyhole porosity from vapour-cavity collapse;
- insufficient energy input or overlap produces irregular lack-of-fusion
  porosity, often with unmelted powder;
- spatter and denudation affect surface quality and can seed near-surface
  defects;
- powder reuse and oxygen content shift the defect population.

Scan strategy sets residual stress and the direction of columnar grain growth
relative to the build axis; `build-orientation` covers the resulting
anisotropy. Confirm the predicted defect population against measurement
(`xct`, `fractography`) rather than reporting it as observed.

## Return

The full parameter set with nominal-versus-verified status and qualification,
the melt-pool regime and defect mechanism it implies, and the microstructure
and anisotropy consequence.
