---
name: install-orca
description: When the ASE connector's ORCA calculator reports binary_missing or the person wants ORCA, explain what only they can do (register, accept the licence, download the tarball), install it (unpacked, or with Spack's manual-download recipe), point the ASE connector at it, and check it runs. Untested here: no ORCA install was available.
keywords: [orca, dft, licence, install, level:L2]
---

# Set up ORCA for the ASE connector

ORCA is free for academic use under its own licence, after registration on the ORCA
forum. **Only the person can register, accept the licence and download it**; never
download ORCA for them or from another source.

1. Tell them: register at the ORCA forum (orcaforum.kofo.mpg.de), accept the licence,
   download the build for their system, and unpack it in a folder they choose.
2. Ask with `ask_user` whether they will unpack it themselves (then ask for the path of
   the `orca` program) or want you to install the tarball they downloaded with Spack's
   `orca` recipe, which takes a manually downloaded file: put the tarball in a Spack
   mirror or the current folder as the recipe's error message names it, then
   `$SPACK install orca` with the confined environment from the fdmnes plugin's
   `install-fdmnes` skill, and `$SPACK location -i orca`.
3. Set the ASE connector's **ORCA program** value to that path. ORCA must be called by its
   full path for parallel runs; the calculator setting `nprocs` adds a `%pal` block, which
   also needs Open MPI on PATH.
4. Call `calculators` to confirm ORCA is found, then run the calculation again.

Until then, offer a calculator that is ready (`calculators` lists them) and say what
changes.
