---
name: xanes-comparison
description: Use when the person wants X-ray absorption spectra of a material compared - between inequivalent absorbing sites, between candidate structures, or with their measurement - from a structure to one spectrum per site, with the person picking the site.
keywords: [alembic, xanes, fdmnes, absorbing site, experiment]
---

# Comparing XANES spectra

- **Structure:** a CIF from the person or `fetch_materials_project` (several materials can
  match). Burette shows it with its unit cell.
- **Sites:** the inequivalent sites of the absorbing element come from the structure
  (symmetry, coordination number and geometry computed in code: tetrahedral,
  octahedral, ...). A site is identified by its coordination and one atom index.
- **Calculations:** one per site (`run_xanes` with `absorber` as that site's index), with
  the same settings for all so the spectra compare; `xanes` covers radius convergence.
- **Overlay** of the normalized spectra (`chemistry-views`). A selection of an energy range
  on the overlay comes back as rows; those rows and the sites' geometry (pre-edge
  intensity and site symmetry) answer a question about it.
- **The person's measurement:** `compare_spectra` with `align: true` gives the shift and
  the agreement measures, and agreement has limits on what it proves.

An atom the person selects in Burette belongs to a site the structure identifies (its
coordination computed in code); the picture alone does not tell sites apart.
