---
name: install-nwchem
description: When the ASE connector's NWChem calculator reports binary_missing, find an NWChem already installed, or install it once with the person's consent (conda or Spack, in the home folder with a launcher on PATH) so every conversation finds it, or go on with a calculator that is ready.
keywords: [nwchem, dft, spack, conda, install, level:L2]
---

# Get NWChem for the ASE connector

NWChem is free (ECL-2.0). The ASE connector finds it through its **NWChem program** value
or `nwchem` on PATH.

## Look first

`binary_missing` means only that the connector found no NWChem where it looks: its **NWChem
program** value and `nwchem` on PATH. NWChem may be elsewhere: in a conda environment
(`conda env list`), a Spack install (`spack find -p nwchem`), a cluster module (`module avail
nwchem`), or `~/.local/opt/nwchem`. Before offering an install, look there yourself, and ask
the person when you cannot tell. When you find one, ask with `ask_user` whether to use it
(name its path). Once the person agrees, set **NWChem program** (`nwchem`) to it with
`set_connector_value`, a module's program by its full path; the value belongs to this
conversation, so tell them they can save it as their default in the ASE connector's settings.

## Ask first

Ask once with `ask_user`: **install it now** (Spack builds it from source in tens of
minutes with MPI and maths libraries; conda installs a prebuilt one in minutes), **I'll
install it myself**, or **use a calculator that is ready** (`calculators` lists them; say
what changes, for example xTB instead of DFT).

## Install once, for every conversation

Install under `~/.local/opt` (never inside a workspace, which would install it again for
each one) and put a launcher in `~/.local/bin`, which is on CLIO's PATH:

- **conda (fastest):** with `conda`, or the standalone `micromamba` when conda is absent:
  `conda create -y -p "$HOME/.local/opt/nwchem" -c conda-forge nwchem`.
- **Spack:** with the environment from the fdmnes plugin's `install-fdmnes` skill,
  `$SPACK install nwchem` (Spack's own recipe), then `$SPACK location -i nwchem`.

The conda build carries its build machine's basis-library path, so the launcher sets it:

```sh
nw="$HOME/.local/opt/nwchem"
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/nwchem" <<EOS
#!/bin/sh
export NWCHEM_BASIS_LIBRARY="$nw/share/nwchem/libraries/"
export NWCHEMRC="$nw/etc/default.nwchemrc"
exec "$nw/bin/nwchem" "\$@"
EOS
chmod +x "$HOME/.local/bin/nwchem"
```

Running as root in a container, Open MPI also needs `OMPI_ALLOW_RUN_AS_ROOT=1` and
`OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1` exported in the launcher.

## Check

Call `calculators`: NWChem is ready with no setting. A run of H2 at a small basis checks
the basis library before the real calculation (an `exit 255` with a basis error in its
output means the library path is wrong). For parallel runs the calculator setting `nprocs`
adds `mpirun -np`.
