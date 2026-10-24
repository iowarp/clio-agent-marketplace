---
name: mechanical-testing
title: Design and Report a Mechanical Test or Fatigue Campaign Against a Named Standard
description: Specify a mechanical test's type, governing standard, control mode and specimen before running or interpreting it; for fatigue campaigns, define loading, failure and runout criteria and treat runouts as censored data.
keywords:
- level:L1
- mechanical-testing
- fatigue-testing
---

## Any test

- **Type and standard.** Name the test and its governing standard (for
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
  anisotropic material all change the result independently of the material.
  Report them, or a specimen effect will be mistaken for a material effect.
- **Instrumentation.** Check that the load frame, load cell, extensometer and
  acquisition can resolve what the study needs (`load-frame-capability`,
  `experimental-data-acquisition`).

For tensile tests, `tensile-testing` covers rate, extensometry and
engineering versus true stress-strain.

## Fatigue campaigns

- **Loading.** State stress or strain amplitude or range, mean stress or
  R-ratio, waveform and frequency. A cycles-to-failure number without R-ratio
  and amplitude is not usable stress-life or strain-life data.
- **Failure and runout criteria, set before testing.** Define failure
  (separation, a stated stiffness drop, a crack of stated length) and the
  runout cycle count at which a specimen is stopped. Runouts are censored
  observations, not failures: never drop them or count them as failures at the
  runout count. Fit them with a method that handles censoring (`statistics`).
- **Scatter.** Large life scatter at a fixed amplitude is common and expected,
  not a sign of a bad test. One specimen does not establish a point on a life
  curve without repeats or a stated confidence level.

## Connecting to simulation

When simulation predicts a critical region, translate it into what the test
must measure: instrumentation placement, expected range, and whether the
specimen geometry exposes that region at all. A predicted hotspot the setup
cannot observe is not validated by running the test anyway.

## Return

The test type, standard, control mode and specimen specification; for fatigue,
the loading, the failure and runout criteria, and the raw life data with
censoring flagged; and the specimen, geometry and orientation the data applies
to.
