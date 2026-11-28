---
name: defect-driven-fatigue
title: Predict Fatigue Life From a Measured, Specific Defect
description: Connect a measured defect's size and location to the local stress state at that exact location, and use a defect-size-based life model rather than a smooth-specimen S-N curve.
keywords:
- level:L1
- fatigue
---

This skill covers parts where a specific defect (pore, inclusion,
lack-of-fusion region) is known or suspected to control fatigue initiation,
common for additively manufactured parts (see `xct`), as opposed to an
idealized defect-free material.

Fatigue life from a defect-driven model is governed by the combination of the
defect's measured size (typically an equivalent area or √area metric), its
exact location, and the local stress state at that specific location from
`stress-strain-analysis`; a nominal or section-average stress misses it. A
surface-breaking defect is generally more damaging than an internal one of
the same size at the same nominal stress.

Life models include a √area-based approach such as Murakami's, or a
fracture-mechanics treatment of the defect as an initial crack via
`fracture-mechanics`, each with its calibration material and condition. A
model calibrated on one alloy's defect population does not transfer to
another without validation. The predicted life is sensitive to the assumed
defect size.
