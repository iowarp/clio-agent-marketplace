---
name: experimental-data-acquisition
title: Verify Data Acquisition Settings Against the Signal Being Measured
description: Check sampling rate, filtering, and channel calibration against the physical signal being captured, before treating logged data as a faithful record.
keywords:
- level:L1
- mechanical-testing
---

A sampling rate is adequate relative to the fastest signal feature being
captured: one too low relative to a fatigue test's cyclic frequency or a
dynamic event aliases or misses peak values, so the margin (e.g., a multiple
of the highest frequency of interest) is part of the setup.

Filtering (analog or digital, cutoff frequency, filter order) that removes
noise can also attenuate a real signal feature if its cutoff is too close to
the frequency of interest; it is safe only when checked.

Each channel's calibration (load, strain, displacement, temperature) is
current and traceable or it is not, and the units and any scaling applied in
the acquisition software travel with the data: a unit or scaling error at
acquisition silently propagates through every downstream analysis.
