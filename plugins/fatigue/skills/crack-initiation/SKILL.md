---
name: crack-initiation
title: Identify the Crack-Initiation Mechanism and Site
description: Determine whether initiation is surface- or defect-driven and at which specific site, since the mechanism determines which mitigation is actually effective.
keywords:
- level:L1
- fatigue
---

Initiation mechanisms differ in mitigation: surface-initiated (from surface
roughness, a machining mark, or a persistent slip band at a free surface;
mitigated by surface finishing or peening, see `post-processing`) versus
internal/defect-initiated (from a subsurface pore or inclusion; mitigated by
defect control in `am-process-parameters` or by HIP in `post-processing`). A
surface treatment does not address an internally-initiated failure, and vice
versa.

Fractographic evidence (`fractography`) locates the actual initiation site on
a failed specimen; geometry alone only predicts it. A predicted stress
concentration and the actual initiation site can disagree when an internal
defect happens to dominate over the nominal stress raiser.

The initiation life fraction relative to total life can sometimes be
estimated (from fractography, from a striation count, or from a crack-growth
calculation in `fracture-mechanics`): a short initiation life relative to
total life indicates a defect-dominated case, which shows which mitigation has
the most leverage.
