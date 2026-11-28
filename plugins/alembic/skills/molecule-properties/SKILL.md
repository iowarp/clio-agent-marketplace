---
name: molecule-properties
description: Use when the person wants a molecule's optimized geometry, frequencies, IR spectrum, enthalpy, entropy or Gibbs energy - from a structure to checked properties, with the person checking the structure and any imaginary mode along the way.
keywords: [alembic, optimization, frequencies, thermochemistry, imaginary mode]
---

# From a structure to checked properties

- **Method:** `method-ladder` weighs the options; the person may name one.
- **Optimization** (`run_ase` driver `opt`, or `vib`, `thermo`, `ir`, which optimize
  first). Its convergence reads well as a dashboard: the trajectory in the Burette view
  and the energy-and-force chart from `opt_steps.csv`, linked by frame (`burette-views`,
  "In a dashboard"), where the person can pick a step. The trajectory answers a question
  about a step (which atoms moved, by how much), computed in code.
- **Checks:** `geometry-and-frequencies`. An imaginary mode plays in Burette (`play_mode`
  with the mode's animation) for the person to look at; displacing along it
  (`displace_along_mode`) and re-optimizing leaves it, and the checks then apply again.
- **Properties:** frequencies table and IR spectrum, thermochemistry at the stated
  temperature and pressure (`thermochemistry`), with the spin state named.
- **Restarts and edits:** a frame the person picked (`trajectory_frame`) or a geometry
  they edited in Burette arrives as a file the next calculation can start from. Its energy
  compares with the earlier result, in code, only at the same level of theory.
