---
name: xanes
description: Use when a question involves an X-ray absorption spectrum (XANES, the near-edge region) - simulating one for a structure, comparing a calculation with a measurement, or reading oxidation state, coordination or site symmetry from edge and pre-edge features.
keywords: [xanes, xas, spectroscopy, absorption edge, oxidation state, level:L1]
---

# X-ray absorption near-edge spectra

A XANES spectrum is the absorption of one element's core level (the edge: K for 1s, L2/L3
for 2p, ...) as the photon energy crosses its binding energy. Its shape reflects the
absorber's empty states and the arrangement of its neighbours.

## What the features mean

- **Edge position (E0):** shifts to higher energy with oxidation state, a few eV per unit
  for 3d metals. Compare positions only between spectra aligned the same way.
- **Pre-edge** (K edges of transition metals): weak transitions to d states; their
  intensity rises when the site lacks inversion symmetry (tetrahedral more than
  octahedral). Needs quadrupole terms in a calculation.
- **White line:** the first strong maximum after the edge.
- **Post-edge oscillations:** set by neighbour distances; a larger cluster resolves more
  of them.

## Simulating a spectrum

- **The absorber** is an element (all its sites, averaged) or chosen sites. Ask which,
  when a structure has several inequivalent sites of interest.
- **Method:** multiple scattering with a muffin-tin potential is fast and the usual first
  pass; a full-potential finite-difference calculation is slower and better for
  low-symmetry sites and pre-edges.
- **Cluster radius:** check convergence: run at increasing radii until the features stop
  changing. A small radius gives a smooth, featureless spectrum.
- **Self-consistent potential:** improves edge position and pre-edge; check it converged.
- **Energy range:** wide enough below and above the edge to normalize (at least 10 eV
  below and 20 eV above E0).

## Comparing with a measurement

Normalize both (pre-edge line subtracted, divided by the edge step). A calculation's
absolute energy scale is not predictive: align E0 before comparing shapes, and report the
shift applied. Compare feature positions relative to E0 and relative intensities; quote
a similarity measure (R-factor, correlation) over a stated range. Agreement in shape
supports a structural model; it does not prove it.
