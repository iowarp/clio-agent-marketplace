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

- **The field.** `era5_fetch` gives the pressure-level variables for a time
  and region (temperature, humidity, wind, geopotential); a model run's output
  serves too.
- **The path.** The person can draw it on the layered map (`draw` with mode
  `path`) when they have a front or feature in mind; a proposed path across the
  feature needs its reasoning stated.
- **The section.** `cross_section` along the path writes a section file, which
  `clio.section.v1` shows (its `sectionUri`) with the variable switch and the
  path's stations.
- **Soundings.** `soundings` at the stations or points of interest returns
  a profile table (one row per level: `profile`, `pressure`,
  `temperature_c`, `dewpoint_c`, `parcel_temperature_c`, wind) and a
  table of indices per point (surface-based, mixed-layer and most-unstable
  CAPE and CIN, lifted index, LCL). The profiles fit
  `clio.profile-stack.v1`, and each sounding a skew-T (`skew-t-chart`).
- **Interpretation** comes from the indices and the profiles together: where the
  parcel is warmer than the environment, the inversion that caps it, the
  moisture depth. Each CAPE value depends on which parcel it uses.