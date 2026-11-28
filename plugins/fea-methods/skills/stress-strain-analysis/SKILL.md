---
name: stress-strain-analysis
title: Extract and Interpret Local Stress-Strain State From Simulation Output
description: Report a stress or strain result with the invariant, location, and material-model context that make it meaningful, rather than a single unqualified number.
keywords:
- level:L1
- fea-methods
---

"The stress" is ambiguous: von Mises, maximum principal, a specific tensor
component, or an invariant appropriate to the failure mode (maximum shear for
ductile yielding, maximum principal for brittle fracture, a critical-plane
quantity for multiaxial fatigue) are different quantities, and the wrong one
for the question is common.

A value's location matters: element/node, distance from a free surface or
stress concentration, and whether it is a peak (single element) or an
averaged/extrapolated value. Peak stress at a singular geometric feature
(sharp corner) is mesh-dependent, not converged.

A stress-strain result holds under its material model (linear elastic,
elastic-plastic with a specific hardening law): a "stress" beyond the
material's yield point from a linear-elastic model is not a physically
meaningful stress value.
