---
name: ocean-circulation
title: Ocean Circulation
description: Compute transports through sections and the overturning streamfunction, tidal harmonics and spectra, eddies from sea level and their crossings, SWOT swaths against gridded products, and Lagrangian particle pathways.
keywords:
- level:L1
- ocean
- circulation
- transport
- tides
---

# Ocean circulation

## Transports and overturning

`transport` integrates velocity through a section; the result depends on the
reference level (or whether velocities are absolute) and the section's ends.
`overturning` integrates on the model's own grid in depth or density space, from
a per-cell transport or velocity with cell widths, and which variables were used
changes the result. A published estimate is comparable only when the period and
definition match; anything that differs qualifies the comparison.

## Tides and spectra

`harmonics` fits tidal constituents to a current or sea-level series and
predicts; the constituents' amplitudes, phases, the fraction of variance
explained and the record length (it limits which constituents separate) describe
the fit. `spectra` gives power and rotary spectra; the window and the degrees of
freedom define their uncertainty.

## Sea level

`sea_level_decompose` compares gauge and altimetry trends over their common
period; the period and the vertical land motion assumption qualify it.

## Eddies and SWOT

`eddy_track` identifies and tracks eddies in sea-level maps (a separate
process; py-eddy-tracker, GPL-3.0). `track_crossings` finds where tracks
cross a line or ship track. Its defaults are a starting point, not an answer:

- The high-pass `wavelength_km` removes features larger than it. In a basin
  not much wider than it, it also weakens the basin's own large rings; the right
  value depends on the eddies expected there.
- Track lengths mean something against what is known of the region: rings that
  live for months but come out as tracks of weeks are being broken (`virtual`,
  `shape_error`), and a relaxed run shows whether they join.
- Where the region has a known eddy source (a boundary current that sheds
  rings), which tracks start there, or whether none was shed in the window and
  how that was checked, matters before counting what they did.

`swath_fetch` gets SWOT swaths for a box and
period (searching is anonymous; downloading needs the Earthdata Login in the
Ocean analysis connector), and `swath_compare` sets them against a gridded
field at pass times.

## Particles

`particles` advects particles in a velocity product (Parcels), forward or
backward; the seeding, the time step, the integration scheme and how particles
leaving the domain are handled define the result. The pathways fit a tracks
layer on the map with the time axis.