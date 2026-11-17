---
name: atmospheric-profiles
title: Atmospheric Sections and Soundings
description: Show the vertical structure of the atmosphere - a cross-section along a path the person draws, soundings at points with CAPE, CIN and lifted index, and each sounding as a skew-T.
keywords:
- level:L1
- weather
- sounding
- cross-section
- convection
---

# Atmospheric sections and soundings

1. **The field.** `era5_fetch` the pressure-level variables for the time
   and region (temperature, humidity, wind, geopotential), or use a model
   run's output.
2. **The path.** Ask the person to draw it on the layered map (`draw` with
   mode `path`) when they have a front or feature in mind; otherwise propose
   one across it and say why.
3. **The section.** `cross_section` along the path writes a section file.
   Show it with `clio.section.v1` (its `sectionUri`), with the variable
   switch and the path's stations.
4. **Soundings.** `soundings` at the stations or points of interest returns
   a profile table (one row per level: `profile`, `pressure`,
   `temperature_c`, `dewpoint_c`, `parcel_temperature_c`, wind) and a
   table of indices per point (surface-based, mixed-layer and most-unstable
   CAPE and CIN, lifted index, LCL). Show the profiles with
   `clio.profile-stack.v1` and each sounding as a skew-T (`skew-t-chart`).
5. **Interpret** with the indices and the profiles together: where the
   parcel is warmer than the environment, the inversion that caps it, the
   moisture depth. State which parcel each CAPE uses.
