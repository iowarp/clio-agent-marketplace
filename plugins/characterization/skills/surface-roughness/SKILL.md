---
name: surface-roughness
title: Report Surface Roughness With Its Measurement Parameter and Method
description: Attach a roughness value to the specific parameter, cutoff length, and measurement method that define it, since roughness numbers are not comparable without them.
keywords:
- level:L1
- characterization
---

Roughness parameters differ: Ra (arithmetic mean), Rz (mean peak-to-valley),
Sa (areal mean, from an areal rather than profile measurement), each with its
evaluation/cutoff length. Ra and Sa are not the same quantity and are not
directly convertible without additional assumptions; a value means the
parameter actually measured.

Each measurement method (contact stylus profilometry, `optical-profilometry`,
areal optical scanning) has its own resolution and known limitations: a
contact stylus can under-resolve steep AM as-built features its tip cannot
physically enter, while optical methods can be biased by highly reflective or
steeply sloped as-built surfaces.

On an AM part, an as-built, machined, or finished surface (see
`post-processing`) gives different values, and as-built AM roughness is
typically anisotropic (different on up-facing, down-facing, and vertical
surfaces per `build-orientation`): a single value describes the one surface
it came from.
