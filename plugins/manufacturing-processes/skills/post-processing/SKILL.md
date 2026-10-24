---
name: post-processing
title: Track Post-Processing and Surface Finishing and the State Each Step Produces
description: Treat each post-processing step (stress relief, HIP, heat treatment, support removal, machining, surface finishing, peening) as producing a distinct, traceable part state; state what each step changes and what it leaves untouched, and whether a finishing process reaches every surface it must.
keywords:
- level:L1
- manufacturing
- post-processing
---

## Track the chain

Enumerate the steps applied, in order: stress relief, hot isostatic pressing
(HIP), solution and ageing heat treatment, support removal, machining, surface
finishing, peening. Each step changes the part's state; a property, defect or
characterization result is valid only for the state it was measured in. Label
every reported value with that state: as-built, stress-relieved, HIPed,
heat-treated, machined, finished.

Do not assume a step was performed, or a state reached, without evidence.

## What each step does and does not fix

- HIP closes internal porosity under heat and pressure. It does not close
  surface-connected porosity and does not improve surface roughness.
- Stress relief reduces residual stress without the bulk microstructural
  change of a full solution treatment.
- Heat treatment moves the microstructure between states; its schedule and
  mechanism are in `heat-treatment`.
- One step's benefit does not imply another's.

## Choosing a surface-finishing process

State the starting surface (as-built, as-machined) and the requirement
(roughness value, fatigue performance, appearance) before choosing a process;
material removal differs by orders of magnitude between light polishing and
abrasive flow machining. Name the process and its mechanism:

- machining and grinding remove material to a controlled geometry;
- abrasive, chemical and electrochemical polishing reduce peak roughness
  without necessarily removing subsurface defects;
- shot and laser peening introduce compressive residual stress at the surface,
  mainly for fatigue, not for roughness.

Do not conflate a roughness-reduction process with a residual-stress process;
a requirement may need both, deliberately. For internal or hard-to-reach
surfaces (channels, lattices), state whether the process can physically reach
them: one validated on external surfaces does not automatically reach
internal ones.

## Return

The chain applied in order, what each step changed and left untouched, the
resulting part state, which state each measurement describes, and for
finishing whether it was verified to reach every surface the requirement
covers.
