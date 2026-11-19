---
name: fdmnes-xanes
title: XANES with FDMNES
description: Use when an X-ray absorption near-edge spectrum is to be computed with the FDMNES connector for a crystal or molecule file, or a computed or measured spectrum is to be normalized or compared with others.
keywords: [fdmnes, xanes, xas, spectrum, level:L2]
---

# XANES with the FDMNES connector

Read `xanes` for what the spectrum means and which settings matter. This skill
is how the connector does it.

## Structures from the Materials Project

`fetch_materials_project` takes a formula or an `mp-` id and writes a CIF for each
matching material, ordered by energy above the hull, with space group and magnetic
ordering. When several match (polymorphs, magnetic orderings), say which one you use and
why, or ask. It needs the connector's **Materials Project API key**. On `mp_key_missing`
ask once with `offer_plugin` (plugin `fdmnes`, your reason, `needs` with the key's need
from the listing's `optional_needs`): the person types it into the card, never into the
chat. Do not look for another source unless they choose Not now. Show the structure with
its unit cell in Burette before computing.

## run_xanes

- `structure`: a CIF or POSCAR for a crystal (FDMNES finds the symmetry and computes the
  inequivalent sites), an XYZ, SDF or PDB for a molecule or cluster.
- `absorber`: always given. An element (`"Fe"`: every site of it) or 0-based site
  indices (one spectrum each). Ask the person when the structure has several elements or
  inequivalent sites and the question does not say.
- `edge` (K, L23, ...), `method` (`green` first; `fdm` for pre-edges and low symmetry),
  `radius` (Å), `scf`, `quadrupole` (pre-edges of 3d-metal K edges), `magnetism`,
  `energy_range`.
- It reports the threshold and edge energy, inequivalent absorbing sites, point group,
  cluster size and SCF cycles, and for each spectrum E0, white line, edge step and peaks.
  Files: `spectrum.csv` (`energy_eV` from the Fermi level, `photon_energy_eV`, `mu`,
  `mu_norm`), `result.json`, FDMNES's input and logs.

Time: a small crystal with `green` takes seconds to minutes; `fdm` and large radii take
much longer. Check convergence with radius on one site before a large run, and use
`timeout_s` for exploratory runs.

## Spectra

- `read_spectrum` normalizes an FDMNES output or a measured spectrum (two columns,
  energy and absorption), optionally shifting its energies.
- `compare_spectra` with `align: true` shifts each spectrum's E0 onto the first's and
  reports R-factor and correlation on one grid. Always align a calculation with a
  measurement; say the shift.
- Plot spectra from the CSV files (energy against `mu_norm`), one line per spectrum.

When `run_xanes` answers `binary_missing`, use `install-fdmnes`. `fdmnes_failed` carries
FDMNES's last output lines: read them, and read `xanes_bav.txt` in the run folder before
changing settings.
