---
name: boundary-conditions
title: Justify Boundary Conditions Against the Physical System They Represent
description: Treat every boundary condition and load as a modeling assumption that must match the real support and loading it stands in for, not a default the software supplies.
keywords:
- level:L1
- fea-methods
---

Each boundary condition represents something physical (a fixed support, a
symmetry plane, a bolted joint idealized as fully constrained), and that
idealization is conservative, unconservative, or of unknown bias relative to
the real system. A "fixed" boundary condition is rarely physically exact; it
approximates something and biases the result in one direction.

Loads are idealizations the same way: point loads representing a distributed
pressure, a simplified load case standing in for a real duty cycle, or a load
magnitude/direction taken from a separate analysis (e.g., a predicted service
load) with its own uncertainty.

Boundary conditions produce artifacts: an overly stiff support or a point load
produces a local stress singularity that does not reflect real behavior. A
governing stress that sits on such an artifact is a boundary-condition
artifact, not a physical result.
