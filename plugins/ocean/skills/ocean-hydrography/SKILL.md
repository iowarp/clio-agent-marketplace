---
name: ocean-hydrography
title: Ocean Hydrography
description: Turn CTD casts, Argo floats and glider profiles into TEOS-10 properties, water masses against a stated definition, mixed layer depth and stratification, and sections - with the views a physical oceanographer checks them in.
keywords:
- level:L1
- ocean
- hydrography
- water-masses
---

# Ocean hydrography

## Profiles in

- Cast files: `ctd_read` (SBE CNV, WHP-exchange, NetCDF, CSV) into one
  profile table (one row per sample: `profile`, `time`, `latitude`,
  `longitude`, `pressure` and the variables). The files carry quality flags,
  and which were kept shapes the data.
- Argo: `argo_fetch` for a box and years, or for floats; the data mode and QC
  filter shape the data. Gliders: `glider_fetch` for a deployment.

## Properties

`teos10` adds Absolute Salinity, Conservative Temperature, potential density
and buoyancy frequency. TEOS-10 derivations are defined on these, not on
practical salinity and in-situ temperature.

## Water masses

`water_masses` assigns each sample against a definition: a built-in regional one
or a custom one (name, SA-CT polygon or ranges, pressure range) for the region.
The definition and its source are part of the result; unassigned samples are a
finding, and forcing them into a class hides it. When the person moves a
boundary, a rerun with their definition shows what changed.

## Profile metrics

`profile_metrics` for mixed layer depth (a stated density or temperature
criterion and reference depth), stratification, anomalies on standard
levels and vertical type. Each value depends on its criterion; seasonal
cycles and trends come from these per profile, with the number of profiles
per period.

## Sections

`section` along a ship track or a path the person draws on the map, from
profiles or from gridded output. It writes a section file for
`clio.section.v1` (its `sectionUri`), and the path is what reproduces it.

## Views

- The section, and a T-S diagram with density contours (`ts-diagram`),
  linked by cast: a shared `/selection/<key>` on `profile` highlights the
  same cast in both.
- Many profiles: `clio.profile-stack.v1`, with `excluded` bound so the
  person can drop bad profiles; the list comes back for a rerun without them,
  and who excluded which is part of the record.
- Positions: `clio.layered-map.v1` with a points or tracks layer.