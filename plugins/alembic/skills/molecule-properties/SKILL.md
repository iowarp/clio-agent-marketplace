---
name: molecule-properties
description: Use when the person wants a molecule's optimized geometry, frequencies, IR spectrum, enthalpy, entropy or Gibbs energy - from a structure to checked properties, with the person checking the structure and any imaginary mode along the way.
keywords: [alembic, optimization, frequencies, thermochemistry, imaginary mode]
---

# From a structure to checked properties

1. **Method:** pick with `method-ladder`; say which and why in a line. The person may
   name one.
2. **Optimize** (`run_ase` driver `opt`, or `vib`, `thermo`, `ir`, which optimize first).
   Show the convergence as an energy-and-force chart linked to the viewer by step
   (`chemistry-views`), and the final structure. A question about a step is answered from
   the trajectory (which atoms moved, by how much), computed in code.
3. **Check** with `geometry-and-frequencies`. An imaginary mode: play it in Burette
   (`play_mode` with the mode's animation), let the person look, then displace along it
   (`displace_along_mode`) and re-optimize, and check again.
4. **Properties:** frequencies table and IR spectrum, thermochemistry at the stated
   temperature and pressure (`thermochemistry`), with the spin state named.
5. **Restarts and edits:** a frame the person picked (`trajectory_frame`) or a geometry
   they edited in Burette arrives as a file: start the next calculation from that file and
   compare energies with the earlier result in code, only at the same level of theory.

Report numbers with units, the method, the checks, and the files.
