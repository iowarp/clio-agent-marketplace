---
name: fatigue-life-prediction
title: Select and Apply a Fatigue Life-Prediction Method With Its Inputs Traced
description: Choose a life-prediction method that matches the regime and loading actually present, and trace every input it consumes back to its source.
keywords:
- level:L1
- fatigue
---

The method follows from the regime and loading already established
(`fatigue-mechanics`, `multiaxial-fatigue`): S-N/`high-cycle-fatigue` for
elastic-dominated uniaxial loading, a critical-plane method
(`fatemi-socie`) for multiaxial non-proportional loading, a
fracture-mechanics crack-growth approach (`fracture-mechanics`) when an
initial defect size is known and the question is remaining life, or a
defect-driven approach (`defect-driven-fatigue`) when a specific measured
defect controls initiation.

Every input traces to a source: local stress/strain state from simulation
(`stress-strain-analysis`), material cyclic properties from testing or
literature, and any defect size from characterization (`xct`). A life
prediction is only as reliable as its least-certain input, and one input
usually dominates the uncertainty.

A predicted life is a band, not a single number: scatter in fatigue data (see
`mechanical-testing`) and input uncertainty both propagate into the
prediction, and a design decision needs the band, not just the mean estimate.
