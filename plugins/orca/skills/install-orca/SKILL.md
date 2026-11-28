---
name: install-orca
description: When the ASE connector's ORCA calculator reports binary_missing or the person wants ORCA, explain what only they can do (register, accept the licence, download the tarball), install it (unpacked, or with Spack's manual-download recipe), point the ASE connector at it, and check it runs. Untested here: no ORCA install was available.
keywords: [orca, dft, licence, install, level:L2]
---

# Set up ORCA for the ASE connector

ORCA is free for academic use under its own licence, after registration on the ORCA
forum. **Only the person can register, accept the licence and download it**; the agent
can never download ORCA for them or from another source.

- **Where ORCA may already be:** `binary_missing` means only that the connector found no
  ORCA where it looks (its **ORCA program** value and `orca` on PATH). The person may have
  unpacked ORCA already: an `orca` program beside `orca_scf` (`find ~ /opt -maxdepth 4
  -name orca_scf`; `orca.exe` on Windows), a module (`module avail orca`) or a Spack
  install (`spack find -p orca`), or the person knows where it is. Using one that is found
  is the person's decision (`ask_user`, naming its path).
- **What only the person does:** register at the ORCA forum (orcaforum.kofo.mpg.de),
  accept the licence, download the build for their system, and unpack it in a folder they
  choose.
- **Who installs it** is the person's choice (`ask_user`): they unpack it themselves (and
  know the path of the `orca` program), or the tarball they downloaded goes through
  Spack's `orca` recipe, which takes a manually downloaded file: the tarball goes in a
  Spack mirror or the current folder as the recipe's error message names it, then
  `$SPACK install orca` with the confined environment from the fdmnes plugin's
  `install-fdmnes` skill, and `$SPACK location -i orca`.
- **Pointing the connector at it:** the ASE connector's **ORCA program** value holds that
  path. ORCA is called by its full path for parallel runs; the calculator setting
  `nprocs` adds a `%pal` block, which also needs Open MPI on PATH.
- **A working install:** `calculators` shows ORCA found.

Until then, a calculator that is ready (`calculators` lists them) is an alternative that
changes what the result means.
