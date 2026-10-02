---
name: size-and-growth-traits
title: Size and Growth Traits
description: DRAFT. Check and analyse plant size and growth from image- or scan-derived traits - pixel vs metric units, projected (2D) vs 3D size, saturation and clipping, and growth curves over repeated measures. Use for any question about plant size, biomass proxies, or growth rate.
keywords:
- level:L1
- phenotyping
- growth
---

# Size and growth traits (draft)

Size traits come from segmentation masks (2D images) or surfaces/point clouds
(3D scans). They are proxies: projected area, height, volume-like products,
and pot weights all measure something related to, but not equal to, biomass.

## Checks before any comparison

1. **Scale.** Pixel values are only comparable within one camera setup. For
   any metric value, check the conversion: object size against the documented
   frame, container, or tray size; the same trait from another instrument
   (2D projected area vs a 3D scan's projected area). A disagreement by a
   large factor means the metric scale is suspect -- use pixels within a
   sensor, and ask the owners.
2. **Mask choice.** A trait computed on a different mask (vendor vs ML model,
   or different thresholds) is a different method. Check which mask each
   value used and do not mix them.
3. **Saturation and clipping.** For each session, compute the fraction of
   units whose bounding box touches the crop/frame edge, and the median trait
   over time. A plateau that coincides with edge contact or canopy overlap is
   a measurement limit. Truncate or flag growth curves from that point on.
4. **Empty masks.** Zero-coverage rows are missing values, not tiny plants.
5. **Weights.** Pot weight includes pot, substrate, and water; watering events
   dominate it. Do not read pot weight as plant mass without a documented
   tare and a watering model.
6. **Repeated sessions per day.** Size can differ between morning and evening
   sessions (leaf movement, turgor). Fix one session per day or average per
   day before fitting curves.

## Growth curves

- One curve per unit: trait vs time (days after sowing/treatment if known;
  otherwise days since first session, stated as such).
- Summaries: area under the curve, final size before any clipping onset,
  absolute and relative growth rate over a window (relative growth rate on
  log-scale values), time to reach a threshold.
- Fit smooth models (logistic, Gompertz, or splines) only on the unclipped
  part; report the window used.
- Compare groups with the repeated-measures methods in `treatment-response`,
  not with one t-test per day.

## Report

State units and their tag (stated/checked/inferred), the mask/method, the
session choice, the clipping cut-off, and how many units each curve group
contains.
