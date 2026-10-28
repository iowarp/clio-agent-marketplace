---
name: microstructure
title: Describe and Measure Microstructure in Terms That Predict Behavior
description: Describe a material's microstructure quantitatively (phases and fractions, grain size and morphology, texture, precipitates, defect population), measure it from optical, electron or EBSD images with preparation artifacts, calibration and sampling controlled, and connect it to the process that made it and the properties it controls.
keywords:
- level:L1
- materials
- microstructure
- characterization
---

## Describe it quantitatively

Use the quantities that predict behavior: phase identity and volume fraction,
grain size and morphology (equiaxed or columnar, unimodal or bimodal),
crystallographic texture, precipitate size and distribution, and the defect
population (porosity, inclusions). A qualitative label ("fine-grained",
"typical additive microstructure") does not support a property claim.

Connect the state to the process that produced it and the property it
controls: columnar grains and texture from directional solidification
(additive manufacturing, casting) give anisotropic properties; a bimodal grain
structure changes strength and fatigue behavior relative to a unimodal one of
the same average size. When the state is inferred from a processing route
rather than measured, say so and name the measurement that would confirm it.

## Measure it from images

Record the technique and conditions: modality (optical, SEM, TEM, EBSD),
signal, magnification and pixel calibration, accelerating voltage, detector,
and the specimen preparation route. Rule out preparation artifacts before
measuring: pull-out, relief, redeposition, ion-beam damage, etching bias,
charging.

- Define the measurand and the standard: grain size by a named method (for
  example the ASTM E112 intercept or planimetric procedure), phase fraction by
  systematic point or area counting, particle size and spacing by a stated
  stereological rule.
- State the number of fields, the total area or line length, and the
  resulting sampling uncertainty. A single representative image is not a
  measurement.
- Guard against section bias: a 2D section under-samples large features and
  mis-measures 3D size and shape unless corrected. For 3D internal features
  use `xct` rather than inferring them from a section.
- For EBSD, report step size, indexing rate and the cleanup applied, and do
  not treat cleaned data as raw.

When image analysis is scripted, keep the script and its parameters with the
results so the measurement can be repeated.

## Return

The microstructural state in quantitative terms; for measurements, the
method, sampling and uncertainty, the artifacts considered and excluded; its
process origin; the properties it is expected to control; and the claims the
current evidence cannot support.
