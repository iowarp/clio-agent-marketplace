---
name: uncertainty-quantification
title: Quantify and Propagate Uncertainty Through a Result Chain
description: Track measurement, model, and sampling uncertainty separately and propagate them explicitly through a chain of calculations rather than reporting a single deterministic answer.
keywords:
- level:L0
- scientific-method
---

Uncertainty in a chain has distinct sources: measurement uncertainty
(instrument resolution/calibration, per the specific technique's skill),
sampling uncertainty (from finite sample size: how many samples, fields, or
scans), and model uncertainty (from an assumed physical, predictive or
statistical model, or a simplification). Some sources get quantified and some
do not, and the difference matters to the reader.

A prediction chaining a simulated quantity, a measured input, and a fitted
model carries each input's uncertainty through to the final result (by
analytical propagation or Monte Carlo sampling); a final number without it
reads as exact.

The input that dominates the total uncertainty is where additional measurement
or refinement would actually reduce uncertainty in the final result; effort
elsewhere would not help.
