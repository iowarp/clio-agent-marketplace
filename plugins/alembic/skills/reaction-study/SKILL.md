---
name: reaction-study
description: Use when the person asks for a reaction energy, enthalpy or Gibbs energy, or compares methods on a reaction - every species computed the same way, a live energy diagram across method levels, and the person choosing what to confirm with DFT.
keywords: [alembic, reaction, gibbs energy, energy diagram, method levels, dft]
---

# A reaction study across method levels

- **The reaction:** balanced in atoms and charge, its species with their spin states
  (`thermochemistry`), open-shell ones named as such.
- **Runs:** one per species and method. They are independent, so they can run in parallel
  where the runtime allows (one `run_ase` call per species, or a fan-out in code). A table
  per species holds path, method, energy, H, S, G, multiplicity and checks.
- **Live energy diagram:** per-species results written to a CSV as each finishes feed a
  reaction energy diagram (`chemistry-views`), one series per method, updating as results
  arrive. In a dashboard with the Burette view linked by the species' structure path
  (`burette-views`, "In a dashboard"), picking a species opens it.
- **Reaction quantities** come from the per-species table with stoichiometry, in code;
  numbers added by hand are where slips come in.
- **Disagreement between methods:** the species where the methods differ most are where
  DFT (NWChem through the ASE connector) adds most; which to confirm is the person's
  choice. Every level side by side shows the spread.
- **A new temperature or pressure** reuses the optimized structures and frequencies.
