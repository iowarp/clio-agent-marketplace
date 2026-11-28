---
name: microstructure
title: Describe and Measure Microstructure in Terms That Predict Behavior
description: Use to describe or measure a material's microstructure (phases, grains, texture, precipitates, defects) from optical, electron or EBSD images and relate it to process and properties.
keywords:
- level:L1
- materials
- microstructure
- characterization
---

## Quantitative description

The quantities that predict behavior are phase identity and volume fraction,
grain size and morphology (equiaxed or columnar, unimodal or bimodal),
crystallographic texture, precipitate size and distribution, and the defect
population (porosity, inclusions). A qualitative label ("fine-grained",
"typical additive microstructure") does not support a property claim.

Connect the state to the process that produced it and the property it
controls: columnar grains and texture from directional solidification
(additive manufacturing, casting) give anisotropic properties; a bimodal grain
structure changes strength and fatigue behavior relative to a unimodal one of
the same average size. A state inferred from a processing route rather than
measured is an inference until a measurement confirms it.

## Measurement from images

A measurement is defined by its technique and conditions: modality (optical,
SEM, TEM, EBSD), signal, magnification and pixel calibration, accelerating
voltage, detector, and the specimen preparation route. Preparation artifacts
(pull-out, relief, redeposition, ion-beam damage, etching bias, charging)
masquerade as microstructure.

- A measurand needs its standard: grain size by a named method (for
  example the ASTM E112 intercept or planimetric procedure), phase fraction by
  systematic point or area counting, particle size and spacing by a stated
  stereological rule.
- The number of fields and the total area or line length set the sampling
  uncertainty. A single representative image is not a measurement.
- A 2D section under-samples large features and mis-measures 3D size and shape
  unless corrected; `xct` measures 3D internal features directly.
- EBSD data depend on step size, indexing rate and the cleanup applied, and
  cleaned data are not raw.

A scripted image analysis, kept with its parameters next to the results, is a
repeatable measurement.
