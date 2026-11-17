---
name: adsorption-screen
description: Use when the person wants gas uptake or working capacity for one or several MOFs or zeolites, or a ranking of frameworks - candidate CIFs to simulated uptakes, with the person selecting which to examine. gRASPA needs a GPU; without one, run folders are prepared for a GPU node.
keywords: [alembic, adsorption, mof, screening, graspa]
---

# An adsorption screen

Untested end to end: gRASPA has not run where this was written (no GPU). Say so when
results come from this path for the first time.

1. **Frameworks:** CIFs from the person, a database they name, or the Materials Project.
   Check each opens (unit cell shown in Burette) and note whether it carries charges.
2. **Conditions:** adsorbate, temperature, pressure(s); for working capacity both
   conditions (`adsorption`).
3. **Where it runs:** `graspa_status`. gRASPA here: `run_graspa`. Otherwise
   `prepare_graspa` per framework and condition and run them on a GPU node
   (`install-graspa`), then `read_graspa`. Without any GPU, say plainly that uptakes
   cannot be computed here, and hand over the prepared folders.
4. **Rank** with `rank_frameworks`; show a scatter and a table with shared selection
   (`chemistry-views`); report excluded frameworks and why.
5. **The person selects** frameworks to examine: open their structures, compare pore and
   metal sites, and rerun with changed settings (charges, cycles) where results are close.
