---
name: size-and-growth-traits
title: Size and Growth Traits
description: Use for questions about plant size, biomass proxies or growth rate from image- or scan-derived traits.
keywords:
- level:L1
- phenotyping
- growth
---

# Size and growth traits

Size traits come from segmentation masks (2D images) or surfaces/point clouds
(3D scans). They are proxies: projected area, height, volume-like products,
and pot weights all measure something related to, but not equal to, biomass.

## What limits a comparison

- **Scale.** Pixel values are only comparable within one camera setup. A metric
  value rests on a conversion that object size against the documented frame,
  container, or tray size, or the same trait from another instrument (2D
  projected area vs a 3D scan's projected area), can confirm. A disagreement by
  a large factor means the metric scale is suspect; pixels within a sensor stay
  valid, and the owners know the real scale.
- **Mask choice.** A trait computed on a different mask (vendor vs ML model,
  or different thresholds) is a different method; values from different masks
  do not mix.
- **Saturation and clipping.** The fraction of units whose bounding box touches
  the crop/frame edge per session, beside the median trait over time, shows it.
  A plateau that coincides with edge contact or canopy overlap is a measurement
  limit, and the growth curve from that point on is not growth.
- **Empty masks.** Zero-coverage rows are missing values, not tiny plants.
- **Weights.** Pot weight includes pot, substrate, and water; watering events
  dominate it. Without a documented tare and a watering model it is not plant
  mass.
- **Repeated sessions per day.** Size can differ between morning and evening
  sessions (leaf movement, turgor), so curves mix that variation in unless one
  session per day, or a daily average, is used.

## Growth curves

- One curve per unit: trait vs time (days after sowing/treatment if known;
  otherwise days since first session, which is a different origin).
- Summaries: area under the curve, final size before any clipping onset,
  absolute and relative growth rate over a window (relative growth rate on
  log-scale values), time to reach a threshold.
- Smooth models (logistic, Gompertz, or splines) are valid only on the
  unclipped part, and the window is part of the result.
- Group comparisons belong to the repeated-measures methods in
  `treatment-response`, not one t-test per day.

A size result depends on its units and their tag (stated/checked/inferred), the
mask/method, the session choice, the clipping cut-off, and how many units each
curve group contains.
