---
name: adsorption-screen
description: Use when the person wants gas uptake or working capacity for one or several MOFs or zeolites, or a ranking of frameworks - candidate CIFs to simulated uptakes, with the person selecting which to examine. gRASPA needs a GPU; without one, run folders are prepared for a GPU node.
keywords: [alembic, adsorption, mof, screening, graspa]
---

# An adsorption screen

Untested end to end: gRASPA has not run where this was written (no GPU), so results from
this path are its first.

- **Frameworks:** CIFs from the person, a database they name, or the Materials Project.
  A unit cell shown in Burette tells whether each opens; whether it carries charges
  changes the result.
- **Conditions:** adsorbate, temperature, pressure(s); working capacity takes both
  conditions (`adsorption`).
- **Where it runs:** `graspa_status` tells whether gRASPA runs here (`run_graspa`).
  Otherwise `prepare_graspa` writes one folder per framework and condition for a GPU node
  (`install-graspa`), and `read_graspa` reads the results back. Without any GPU, uptakes
  cannot be computed here; the prepared folders are what there is to hand over.
- **Ranking:** `rank_frameworks`; a scatter and a table with shared selection
  (`chemistry-views`) show it, with excluded frameworks and the reason for each.
- **The person's selection:** frameworks the person selects can be opened, compared on
  pore and metal sites, and rerun with changed settings (charges, cycles) where results
  are close.
