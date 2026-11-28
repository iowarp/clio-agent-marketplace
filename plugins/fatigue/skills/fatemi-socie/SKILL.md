---
name: fatemi-socie
title: Apply the Fatemi-Socie Critical-Plane Fatigue Parameter
description: Compute and interpret the Fatemi-Socie damage parameter correctly for non-proportional multiaxial fatigue, with its material constant and search procedure stated.
keywords:
- level:L1
- fatigue
---

The Fatemi-Socie method is a shear-strain-based critical-plane parameter
suited to materials and loadings where shear dominates crack initiation and
where non-proportional hardening matters. For proportional loading a simpler
equivalent-stress approach may suffice; `multiaxial-fatigue` covers telling
them apart.

The damage parameter is the shear strain amplitude on the critical plane,
scaled by a material constant k times the ratio of normal stress to yield
strength on that plane. k comes from the material's own multiaxial data; one
borrowed from an unrelated material needs justification.

The parameter is evaluated over all candidate plane orientations at the point
of interest, and the maximizing plane is the critical plane. A value computed
on an assumed plane (e.g., the plane of maximum principal stress) rather than
the true maximizing plane is not the Fatemi-Socie parameter. The parameter
maps to life through the calibrated life curve.
