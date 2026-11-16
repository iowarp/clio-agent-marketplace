---
name: xanes-comparison
description: Use when the person wants X-ray absorption spectra of a material compared - between inequivalent absorbing sites, between candidate structures, or with their measurement - from a structure to one spectrum per site, with the person picking the site.
keywords: [alembic, xanes, fdmnes, absorbing site, experiment]
---

# Comparing XANES spectra

1. **Structure:** a CIF from the person or `fetch_materials_project` (say which material
   when several match). Show it with its unit cell in Burette.
2. **Sites:** find the inequivalent sites of the absorbing element from the structure
   (symmetry, coordination number and geometry computed in code: tetrahedral,
   octahedral, ...). Name each by its coordination and give one atom index of each.
3. **One calculation per site** (`run_xanes` with `absorber` as that site's index), same
   settings for all; check radius convergence on one site first (`xanes`).
4. **Overlay** the normalized spectra (`chemistry-views`). A selection of an energy range
   on the overlay comes back as rows: answer from those rows and the sites' geometry
   (pre-edge intensity and site symmetry).
5. **The person's measurement:** `compare_spectra` with `align: true`; report the shift and
   the agreement measures, and what agreement does and does not prove.

When the person selects an atom in Burette, name its site from the structure (its
coordination computed in code), not by guessing from the picture.
