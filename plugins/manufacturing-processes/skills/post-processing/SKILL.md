---
name: post-processing
title: Track Post-Processing and Surface Finishing and the State Each Step Produces
description: Use when a part goes through post-processing (stress relief, HIP, heat treatment, support removal, machining, finishing, peening), to record the part state each step produces.
keywords:
- level:L1
- manufacturing
- post-processing
---

## The chain

Post-processing is a sequence of steps, in order: stress relief, hot isostatic pressing
(HIP), solution and ageing heat treatment, support removal, machining, surface
finishing, peening. Each step changes the part's state; a property, defect or
characterization result is valid only for the state it was measured in:
as-built, stress-relieved, HIPed, heat-treated, machined, finished.

A step was performed, or a state reached, only when evidence shows it.

## What each step does and does not fix

- HIP closes internal porosity under heat and pressure. It does not close
  surface-connected porosity and does not improve surface roughness.
- Stress relief reduces residual stress without the bulk microstructural
  change of a full solution treatment.
- Heat treatment moves the microstructure between states; its schedule and
  mechanism are in `heat-treatment`.
- One step's benefit does not imply another's.

## Surface-finishing processes

The starting surface (as-built, as-machined) and the requirement (roughness
value, fatigue performance, appearance) decide the process; material removal
differs by orders of magnitude between light polishing and abrasive flow
machining. Processes differ in mechanism:

- machining and grinding remove material to a controlled geometry;
- abrasive, chemical and electrochemical polishing reduce peak roughness
  without necessarily removing subsurface defects;
- shot and laser peening introduce compressive residual stress at the surface,
  mainly for fatigue, not for roughness.

A roughness-reduction process is not a residual-stress process; a requirement
may need both. Internal or hard-to-reach surfaces (channels, lattices) are a
question of whether the process physically reaches them: one validated on
external surfaces does not automatically reach internal ones.
