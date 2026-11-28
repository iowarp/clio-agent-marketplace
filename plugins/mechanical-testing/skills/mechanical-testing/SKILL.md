---
name: mechanical-testing
title: Design and Report a Mechanical Test or Fatigue Campaign Against a Named Standard
description: Use to specify or interpret a mechanical test (type, standard, control mode, specimen), including fatigue campaigns with failure and runout criteria.
keywords:
- level:L1
- mechanical-testing
- fatigue-testing
---

## Any test

- **Type and standard.** A test has a governing standard (for
  example ASTM E8/E8M for tension, ASTM E466 for load-controlled and E606 for
  strain-controlled axial fatigue). "We pulled it to failure" or "we cycled
  it" is neither reproducible nor comparable to another lab's result.
- **Control mode.** Load control holds nominal stress and lets strain respond
  (suited to high-cycle, elastic-dominated fatigue); strain control holds
  strain (needed for low-cycle fatigue where plastic strain dominates). The
  wrong mode for the regime invalidates comparison with standard stress-life
  or strain-life data.
- **Specimen.** Gauge section size and shape, surface condition (machined,
  as-built, polished) and orientation relative to the property axis for
  anisotropic material all change the result independently of the material;
  without them a specimen effect is mistaken for a material effect.
- **Instrumentation.** The load frame, load cell, extensometer and acquisition
  resolve what the study needs or not (`load-frame-capability`,
  `experimental-data-acquisition`).

For tensile tests, `tensile-testing` covers rate, extensometry and
engineering versus true stress-strain.

## Fatigue campaigns

- **Loading.** Stress or strain amplitude or range, mean stress or R-ratio,
  waveform and frequency define it. A cycles-to-failure number without R-ratio
  and amplitude is not usable stress-life or strain-life data.
- **Failure and runout criteria, set before testing.** Failure is a definition
  (separation, a stated stiffness drop, a crack of stated length), and so is the
  runout cycle count at which a specimen is stopped; criteria set afterwards bias
  the data. Runouts are censored observations, not failures: dropping them, or
  counting them as failures at the runout count, biases the fit, and a method
  that handles censoring (`statistics`) uses them.
- **Scatter.** Large life scatter at a fixed amplitude is common and expected,
  not a sign of a bad test. One specimen does not establish a point on a life
  curve without repeats or a stated confidence level.

## Connecting to simulation

A critical region predicted by simulation is something the test measures:
instrumentation placement, expected range, and whether the specimen geometry
exposes that region at all. A predicted hotspot the setup cannot observe is
not validated by running the test anyway.
