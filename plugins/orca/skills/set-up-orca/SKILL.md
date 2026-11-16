---
name: set-up-orca
description: When the ASE connector's ORCA calculator reports binary_missing or the person wants ORCA, explain what only they can do (register and accept ORCA's licence, download it), point the ASE connector at the program, and check it runs.
keywords: [orca, dft, licence, install, level:L2]
---

# Set up ORCA for the ASE connector

ORCA is free for academic use under its own licence, after registration on the ORCA
forum. **Only the person can register, accept the licence and download it**; never
download ORCA for them or from another source.

1. Tell them: register at the ORCA forum (orcaforum.kofo.mpg.de), accept the licence,
   download the build for their system, and unpack it in a folder they choose.
2. Ask with `ask_user` for the full path of the `orca` program once they have it.
3. Set the ASE connector's **ORCA program** value to that path. ORCA must be called by its
   full path for parallel runs; the calculator setting `nprocs` adds a `%pal` block, which
   also needs Open MPI on PATH.
4. Call `calculators` to confirm ORCA is found, then run the calculation again.

Until then, offer a calculator that is ready (`calculators` lists them) and say what
changes.
