---
name: finite-element-analysis
title: Formulate a Finite Element Study From Question to Conclusion
description: Trace one continuous argument from the physical question through idealization, discretization, and solution to what the outputs can actually support.
keywords:
- level:L1
- fea-methods
---

An analysis is one continuous chain: research question and quantity of
interest, physical idealization (2D/3D, linear/nonlinear, static/dynamic),
geometry, material model, `boundary-conditions`, `meshing`, solver procedure,
and outputs. A choice at any link (symmetry assumption, contact definition,
element type) is a modeling decision that changes what the result means, not
a numerical detail.

Idealizations (small vs. large deformation, linear-elastic vs. plastic
material response, quasi-static loading vs. a dynamic/fatigue-cycle
treatment) each need a justification. An idealization valid for one quantity
of interest (peak stress) may not be valid for another (fatigue life,
requiring the full cycle).

Converged or validated means the checks behind it exist (mesh convergence,
sensitivity to boundary-condition assumptions, comparison to an analytical or
experimental benchmark). A study without executed solver evidence is
`GENERATED_NOT_EXECUTED`.
