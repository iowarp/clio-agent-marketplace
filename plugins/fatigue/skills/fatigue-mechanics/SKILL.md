---
name: fatigue-mechanics
title: Reason Over Fatigue Damage Mechanisms and Regime Selection
description: Identify the fatigue regime and controlling mechanism before selecting a life-prediction method, since the wrong regime assumption invalidates the method choice.
keywords:
- level:L1
- fatigue
---

The fatigue regime is set by mechanism, not just cycle count: high-cycle
fatigue (elastic-dominated, typically above ~10^4-10^5 cycles,
`high-cycle-fatigue`) versus low-cycle fatigue (plastic-strain-dominated,
fewer cycles, needing strain-based rather than stress-based life models). The
boundary is material- and loading-dependent, not a fixed cycle count.

Damage has stages: crack initiation (nucleation at a persistent slip band,
surface defect, or internal defect; see `crack-initiation`), crack growth to
critical size (see `fracture-mechanics`), and final fracture. Total life is
the sum of initiation and growth life, and their relative share changes which
mechanism dominates the result and which mitigation (surface treatment vs.
defect control) is effective.

Whether the loading is uniaxial or multiaxial (`multiaxial-fatigue`), and
whether a defect is expected to control initiation (`defect-driven-fatigue`),
each changes the applicable life-prediction method in
`fatigue-life-prediction`.
