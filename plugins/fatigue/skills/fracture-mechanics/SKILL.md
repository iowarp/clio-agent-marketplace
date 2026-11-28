---
name: fracture-mechanics
title: Apply Linear-Elastic Fracture Mechanics to a Known or Assumed Defect
description: Apply a stress-intensity or crack-growth approach with the defect geometry, loading, and material toughness stated explicitly, rather than assuming LEFM validity.
keywords:
- level:L1
- fatigue
---

Linear-elastic fracture mechanics requires small-scale yielding at the crack
tip relative to specimen/part dimensions. For a ductile material with a large
plastic zone relative to the section, an elastic-plastic fracture mechanics
approach is needed instead, and LEFM there is non-conservative or
meaningless.

The stress-intensity solution has a source (a handbook solution, a calibrated
finite-element result): the geometry factor Y in K = Y·σ·√(πa) depends on
defect shape, location (surface, corner, embedded), and component geometry,
and the wrong geometry factor is a common source of error.

Fatigue crack growth follows a growth law (Paris law or another) whose
calibrated constants have a source and an applicability range. Near-threshold
and near-critical growth rates deviate from the mid-range Paris regime, and
mid-range constants outside that regime misestimate growth rate. A critical
crack size or remaining-life estimate holds within that validity range.
