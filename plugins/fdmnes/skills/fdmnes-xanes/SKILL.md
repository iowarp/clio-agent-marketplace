---
name: fdmnes-xanes
title: XANES with FDMNES
description: Use when an X-ray absorption near-edge spectrum is to be computed with the FDMNES connector for a crystal or molecule file, or a computed or measured spectrum is to be normalized or compared with others.
keywords: [fdmnes, xanes, xas, spectrum, level:L2]
---

# XANES with the FDMNES connector

`xanes` covers what the spectrum means and which settings matter. This skill
is how the connector does it.

## Structures from the Materials Project

`fetch_materials_project` takes a formula or an `mp-` id and writes a CIF for each
matching material, ordered by energy above the hull, with space group and magnetic
ordering. Several can match (polymorphs, magnetic orderings), and each gives a different
spectrum. It needs the connector's **Materials Project API key**. `mp_key_missing` means
the key is not set; `offer_plugin` (plugin `fdmnes`, a reason, `needs` with the key's need
from the listing's `optional_needs`) shows a card where the person types it, so it never
passes through the chat. Burette shows the structure with its unit cell.

## run_xanes

- `structure`: a CIF or POSCAR for a crystal (FDMNES finds the symmetry and computes the
  inequivalent sites), an XYZ, SDF or PDB for a molecule or cluster.
- `absorber`: required. An element (`"Fe"`: every site of it) or 0-based site
  indices (one spectrum each). A structure with several elements or inequivalent sites
  gives a different spectrum for each choice.
- `edge` (K, L23, ...), `method` (`green` first; `fdm` for pre-edges and low symmetry),
  `radius` (Å), `scf`, `quadrupole` (pre-edges of 3d-metal K edges), `magnetism`,
  `energy_range`.
- It reports the threshold and edge energy, inequivalent absorbing sites, point group,
  cluster size and SCF cycles, and for each spectrum E0, white line, edge step and peaks.
  Files: `spectrum.csv` (`energy_eV` from the Fermi level, `photon_energy_eV`, `mu`,
  `mu_norm`), `result.json`, FDMNES's input and logs.

Time: a small crystal with `green` takes seconds to minutes; `fdm` and large radii take
much longer. Convergence with radius on one site is cheap next to a large run, and
`timeout_s` bounds exploratory runs.

## Spectra

- `read_spectrum` normalizes an FDMNES output or a measured spectrum (two columns,
  energy and absorption), optionally shifting its energies.
- `compare_spectra` with `align: true` shifts each spectrum's E0 onto the first's and
  reports R-factor and correlation on one grid. A calculation compares with a measurement
  only after alignment, and the shift is part of the comparison.
- The CSV files plot as energy against `mu_norm`, one line per spectrum.

`binary_missing` from `run_xanes` is covered by `install-fdmnes`. `fdmnes_failed` carries
FDMNES's last output lines, and `xanes_bav.txt` in the run folder has the full log; the
cause is usually there rather than in the settings.
