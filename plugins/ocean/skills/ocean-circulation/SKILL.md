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

`transport` integrates velocity through a section (state the reference
level or whether velocities are absolute, and the section's ends).
`overturning` integrates on the model's own grid in depth or density space;
name the variables used (a per-cell transport, or velocity with cell
widths). Compare with a published estimate only when the period and
definition match, and say what differs.

## Tides and spectra

`harmonics` fits tidal constituents to a current or sea-level series and
predicts; report the constituents' amplitudes, phases and the fraction of
variance explained, and the record length (it limits which constituents
separate). `spectra` gives power and rotary spectra; say the window and
the degrees of freedom.

## Sea level

`sea_level_decompose` compares gauge and altimetry trends over their common
period; give the period and the vertical land motion assumption.

## Eddies and SWOT

`eddy_track` identifies and tracks eddies in sea-level maps (a separate
process; py-eddy-tracker, GPL-3.0). `track_crossings` finds where tracks
cross a line or ship track. `swath_fetch` gets SWOT swaths for a box and
period (searching is anonymous; downloading needs the Earthdata Login in the
Ocean analysis connector), and `swath_compare` sets them against a gridded
field at pass times.

## Particles

`particles` advects particles in a velocity product (Parcels), forward or
backward; state the seeding, the time step, the integration scheme and how
particles leaving the domain are handled. Show the pathways as a tracks
layer on the map with the time axis.
