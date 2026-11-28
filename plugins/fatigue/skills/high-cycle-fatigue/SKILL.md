---
name: high-cycle-fatigue
title: Apply Stress-Based (S-N) High-Cycle Fatigue Analysis
description: Apply an S-N life estimate with its mean-stress correction and fatigue-limit assumption stated explicitly, rather than reading a single curve without qualification.
keywords:
- level:L1
- fatigue
---

Stress-based methods hold where the regime is elastic-dominated (high-cycle,
per `fatigue-mechanics`); a strain-based approach is needed once plastic
strain is significant.

An S-N curve applies to the material, surface condition, specimen geometry,
and R-ratio/mean stress it was generated at. A smooth-specimen S-N curve for
a part with surface roughness, a notch, or internal defects overstates life
unless a correction (surface factor, notch factor, or a defect-driven
approach) is applied; a handbook curve says nothing about a part it does not
represent.

When the service R-ratio differs from the test R-ratio the curve was
generated at, a mean-stress correction (Goodman, Gerber, Walker, or none)
changes the answer, since mean stress materially changes life for a given
stress amplitude. A life estimate from S-N data carries the data's scatter
band.
