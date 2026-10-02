---
name: physiology-signals
title: Physiology Signals
description: DRAFT. Physics and pitfalls of physiology sensors in plant phenotyping - chlorophyll fluorescence (dark vs light adapted), reflectance spectra and vegetation indices, red edge, water bands, and relative units. Use before interpreting fluorescence, multispectral, or hyperspectral traits.
keywords:
- level:L1
- phenotyping
- fluorescence
- spectral
---

# Physiology signals (draft)

## Chlorophyll fluorescence

- **Dark-adapted** measurements give the maximum quantum yield of PSII,
  Fv/Fm = (Fm - Fo) / Fm. Healthy leaves of most species sit in a narrow
  high band; lower values indicate stress or damage. Check the protocol: was
  the plant dark-adapted, and for how long? A value labelled Fv/Fm from a
  light-adapted step is not Fv/Fm.
- **Light-adapted** protocols (light curves, quenching analysis) give
  operating efficiency and quenching parameters (PhiPSII / QY at a step, NPQ,
  qP, qN, qL, Y(NPQ), Y(NO)). Values depend on the light step; compare the
  same step across plants. Step names usually encode the light level or the
  recovery phase -- read the protocol docs; mark your reading `[inferred]` if
  the export does not define them.
- **Raw fluorescence levels** (Fo, Fm, Ft) are in arbitrary units that depend
  on camera gain and leaf area; use ratios for comparisons.
- **Plausibility**: yields are fractions in [0, 1]; values outside are
  artefacts (division by near-zero on dim pixels, empty masks). Check vendor
  whole-plant values against mask-median values when both exist.
- **Timing**: fluorescence changes over the day; compare same-session values.

## Reflectance spectra and indices

- **Reflectance** should lie in [0, 1] after white/dark calibration; values
  above 1 or below 0 point to calibration or specular problems.
- **Shape checks** on a median plant spectrum: low in the visible red,
  a steep rise at the **red edge** (roughly 680-750 nm), a high near-infrared
  plateau, and **water absorption** dips in the shortwave infrared (near 1450
  and 1940 nm). A spectrum without these is not vegetation or not reflectance.
- **Indices** (NDVI, PRI, PSRI, SIPI, MCARI, OSAVI and variants) differ
  between implementations: check the formula and the exact bands in the docs
  before comparing to literature values. Record the formula in the card.
- **Wavelength labels**: parse wavelengths from metadata or column names; look
  for near-duplicate band columns (see `onboard-dataset`).
- **Water signals** from a few bands (ratios of reflectance near 950-970 nm
  vs near 1450 nm, or similar) are relative indicators, not percent water
  content, unless the docs give a calibration.

## Units

- `a.u.` (arbitrary units), vendor ratios, and indices are relative: compare
  within one instrument, protocol, and session; do not compare magnitudes
  across instruments or facilities.
- Report the method (sensor, protocol step, mask, aggregation) with every
  value, in the `observations` view's `method` column.
