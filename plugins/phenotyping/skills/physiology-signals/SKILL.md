---
name: physiology-signals
title: Physiology Signals
description: Use before interpreting plant fluorescence, multispectral or hyperspectral traits (chlorophyll fluorescence, vegetation indices, red edge, water bands).
keywords:
- level:L1
- phenotyping
- fluorescence
- spectral
---

# Physiology signals

## Chlorophyll fluorescence

- **Dark-adapted** measurements give the maximum quantum yield of PSII,
  Fv/Fm = (Fm - Fo) / Fm. Healthy leaves of most species sit in a narrow
  high band; lower values indicate stress or damage. The protocol says whether
  the plant was dark-adapted, and for how long; a value labelled Fv/Fm from a
  light-adapted step is not Fv/Fm.
- **Light-adapted** protocols (light curves, quenching analysis) give
  operating efficiency and quenching parameters (PhiPSII / QY at a step, NPQ,
  qP, qN, qL, Y(NPQ), Y(NO)). Values depend on the light step, so only the
  same step compares across plants. Step names usually encode the light level or
  the recovery phase, as the protocol docs define; when the export does not
  define them, any reading of them is uncertain.
- **Raw fluorescence levels** (Fo, Fm, Ft) are in arbitrary units that depend
  on camera gain and leaf area; ratios are what compare.
- **Plausibility**: yields are fractions in [0, 1]; values outside are
  artefacts (division by near-zero on dim pixels, empty masks). Vendor
  whole-plant values and mask-median values cross-check each other when both exist.
- **Timing**: fluorescence changes over the day; same-session values compare.

## Reflectance spectra and indices

- **Reflectance** should lie in [0, 1] after white/dark calibration; values
  above 1 or below 0 point to calibration or specular problems.
- **Shape checks** on a median plant spectrum: low in the visible red,
  a steep rise at the **red edge** (roughly 680-750 nm), a high near-infrared
  plateau, and **water absorption** dips in the shortwave infrared (near 1450
  and 1940 nm). A spectrum without these is not vegetation or not reflectance.
- **Indices** (NDVI, PRI, PSRI, SIPI, MCARI, OSAVI and variants) differ
  between implementations: the formula and the exact bands in the docs decide
  whether a literature value is comparable, and they belong with the analysis
  (a card is optional).
- **Wavelength labels**: wavelengths come from metadata or column names, which
  can contain near-duplicate band columns (see `onboard-dataset`).
- **Water signals** from a few bands (ratios of reflectance near 950-970 nm
  vs near 1450 nm, or similar) are relative indicators, not percent water
  content, unless the docs give a calibration.

## Units

- `a.u.` (arbitrary units), vendor ratios, and indices are relative: compare
  within one instrument, protocol, and session; magnitudes do not compare
  across instruments or facilities.
- A result without its method (sensor, protocol step, mask, aggregation), from
  the available metadata or analysis notes, is not interpretable. An
  `observations` table or a column named `method` is not required.
