---
name: multiaxial-fatigue
title: Recognize and Analyze Multiaxial Fatigue Loading
description: Detect when a stress state is genuinely multiaxial and non-proportional, and route to a critical-plane or equivalent-stress method capable of handling it.
keywords:
- level:L1
- fatigue
---

The stress state that matters is the one at the location of interest, not the
nominal applied load: a nominally uniaxial applied load can produce a
multiaxial local stress state at a notch, fillet, or contact patch due to
constraint. The local stress/strain state from `stress-strain-analysis`, not
the remote applied load, decides whether multiaxial analysis is needed.

Proportional multiaxial loading (principal stress directions fixed in time,
ratio of components constant) differs from non-proportional loading
(directions or ratios rotate through the cycle). A simple equivalent-stress
approach (von Mises amplitude, `high-cycle-fatigue`) can be adequate for
proportional loading but is known to be non-conservative for non-proportional
loading, where a critical-plane method (`fatemi-socie`) is generally needed.

Proportionality is a property of the components over the whole cycle: a
conclusion of "proportional" based on only the peak load misses rotation that
occurs elsewhere in the cycle.
