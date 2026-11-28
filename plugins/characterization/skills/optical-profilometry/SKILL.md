---
name: optical-profilometry
title: Acquire and Interpret Optical Profilometry Data
description: Configure an optical profilometer for the surface being measured and know where the technique's own artifacts can bias a roughness or topography result.
keywords:
- level:L1
- characterization
---

The technique variant (confocal, focus-variation, white-light
interferometry) and its lateral and vertical resolution differ by orders of
magnitude between variants and set what surface features can actually be
resolved.

Each technique has characteristic failure modes on a given surface: data
dropout on highly reflective or very dark regions, and bias on steeply sloped
surfaces (a common issue on as-built AM parts) where the technique cannot
capture a valid reflection. The fraction of the scan area interpolated or
excluded due to dropout bounds confidence in the reported roughness; a high
fraction undermines it.

The filtering that separates roughness from waviness and form (a Gaussian or
robust filter with its cutoff) changes the result: the same raw scan can
produce different roughness values under different filter settings. Which
parameter and cutoff mean what is in `surface-roughness`.
