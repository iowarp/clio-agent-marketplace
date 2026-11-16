---
name: install-nwchem
description: When the ASE connector's NWChem calculator reports binary_missing, install NWChem with the person's consent (Spack in a folder of its own, or conda), point the ASE connector at it, or go on with a calculator that is ready.
keywords: [nwchem, dft, spack, conda, install, level:L2]
---

# Get NWChem for the ASE connector

NWChem is free (ECL-2.0). The ASE connector finds it through its **NWChem program** value
or `nwchem` on PATH.

## Ask first

Ask once with `ask_user`: **install it now** (Spack builds it from source in tens of
minutes with MPI and maths libraries; conda installs a prebuilt one in minutes), **I'll
install it myself**, or **use a calculator that is ready** (`calculators` lists them; say
what changes, for example xTB instead of DFT).

## Install

- **conda (fastest):** `conda create -y -p "$PWD/.conda/nwchem" -c conda-forge nwchem`;
  the program is `.conda/nwchem/bin/nwchem`.
- **Spack, in one folder:** with the environment from the fdmnes plugin's
  `install-fdmnes` skill (everything under `$CLIO_SPACK_ROOT`), `$SPACK install nwchem`
  (Spack's own recipe), then `$SPACK location -i nwchem`.
- **A cluster module:** `module avail nwchem`; use its path.

## Point the connector at it

Set the ASE connector's **NWChem program** value to the full path of `nwchem` (for
parallel runs the calculator setting `nprocs` adds `mpirun -np`). Call `calculators` to
confirm, then run the calculation again.
