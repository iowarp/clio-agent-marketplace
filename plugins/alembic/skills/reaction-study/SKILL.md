---
name: reaction-study
description: Use when the person asks for a reaction energy, enthalpy or Gibbs energy, or compares methods on a reaction - every species computed the same way, a live energy diagram across method levels, and the person choosing what to confirm with DFT.
keywords: [alembic, reaction, gibbs energy, energy diagram, method levels, dft]
---

# A reaction study across method levels

1. **Balance the reaction** (atoms and charge) and list the species with their spin states
   (`thermochemistry`); say which are open-shell.
2. **One run per species and method**, in parallel where the runtime allows (one
   `run_ase` call per species, or a fan-out in code). Keep a table per species: path,
   method, energy, H, S, G, multiplicity, checks.
3. **Live energy diagram:** write the per-species results to a CSV as each finishes and
   show a reaction energy diagram from it (`chemistry-views`), one series per method,
   updating as results arrive, in a dashboard with the Burette view linked by the species'
   structure path (`burette-views`, "In a dashboard"), so picking a species opens it.
4. **Reaction quantities in code** from the per-species table with stoichiometry. Never
   add numbers by hand.
5. **Disagreement between methods:** show where the methods differ most and offer DFT
   (NWChem through the ASE connector) for those species; the person chooses what to
   confirm. Report every level side by side.
6. **A new temperature or pressure** reuses the optimized structures and frequencies.

Record the study in the study log: reaction, species and files, methods, results, checks.
