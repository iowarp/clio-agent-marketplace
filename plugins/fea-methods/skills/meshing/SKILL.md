---
name: meshing
title: Choose and Verify a Mesh for the Quantity of Interest
description: Match element type and density to what the study needs to resolve, and prove convergence rather than assuming a fine mesh is adequate.
keywords:
- level:L1
- fea-methods
---

Mesh density matters at the quantity of interest, not uniformly over the
model: a local stress concentration (fillet, hole, contact patch) needs
refinement proportional to the gradient there, while a global stiffness
result may not. A globally fine but locally under-resolved mesh can still
under-predict a peak stress.

Element type and order (linear vs. quadratic, tetrahedral vs. hexahedral,
reduced- vs. full-integration) each have known failure modes (shear locking,
hourglassing) for specific loading types, so the choice depends on the
analysis.

A quantity the conclusion depends on is converged when refinement changes it
by less than a stated tolerance, at a known mesh density. A single mesh
density with no convergence check does not support a quantitative
conclusion.
