---
name: install-fdmnes
description: When the FDMNES connector reports binary_missing (no FDMNES program), build FDMNES with Spack in a folder of its own with the person's consent, point the connector at it, or go on without computing spectra when the person declines; Linux and macOS.
keywords: [fdmnes, spack, install, level:L2]
---

# Get FDMNES, or go on without it

The FDMNES connector runs an FDMNES program already on the machine and never downloads
one. Reading, normalizing and comparing spectra work without it; only `run_xanes` needs it.

## Look first

`binary_missing` means only that the connector found no FDMNES where it looks: its **FDMNES
program** value and `fdmnes` or `fdmnes_linux` on PATH. FDMNES may be elsewhere: a Spack
install (`spack find -p fdmnes`, or this skill's own `~/.local/opt/clio-spack`), a cluster
module (`module avail fdmnes`), or an unpacked download in another folder. Before offering a
build, look there yourself, and ask the person when you cannot tell. When you find one, ask
with `ask_user` whether to use it (name its path). Once the person agrees, set **FDMNES
program** (`fdmnes`) to it with `set_connector_value`; the value belongs to this conversation,
so tell them they can save it as their default in the FDMNES connector's settings.

## Ask first

Ask once with `ask_user` (a choice), naming what you would do: **build it now** (about a
minute to compile, a few more the first time Spack builds its maths libraries, under 1 GB
in one folder), **I'll install it myself** (give the steps and wait), or **skip computing
spectra** (say what stays unverified). If they decline, do not ask again in this
conversation.

## Build it with Spack, in one folder

Everything Spack writes goes under one folder, `~/.local/opt/clio-spack`, shared by every
conversation and workspace (a folder inside a workspace would build it again for each).
clio-kit's Spack repository (`spack-repo/` in
https://github.com/iowarp/clio-kit) has the `fdmnes` recipe and a config that keeps the
install tree, build stages and caches in that folder.

```sh
export CLIO_SPACK_ROOT="$HOME/.local/opt/clio-spack"
export SPACK_USER_CONFIG_PATH="$CLIO_SPACK_ROOT/user-config"
export SPACK_USER_CACHE_PATH="$CLIO_SPACK_ROOT/user-cache"
export SPACK_DISABLE_LOCAL_CONFIG=1
# Spack itself, if `spack` is not on PATH:
git clone --depth 1 -b releases/v1.0 https://github.com/spack/spack "$CLIO_SPACK_ROOT/spack"
# The clio recipes:
git clone --depth 1 https://github.com/iowarp/clio-kit "$CLIO_SPACK_ROOT/clio-kit"
export CLIO_KIT_SPACK_REPO="$CLIO_SPACK_ROOT/clio-kit/spack-repo"
SPACK="$CLIO_SPACK_ROOT/spack/bin/spack -C $CLIO_KIT_SPACK_REPO/config"
$SPACK compiler find
$SPACK install fdmnes
# A launcher on CLIO's PATH, so every conversation finds it:
mkdir -p "$HOME/.local/bin" && ln -sf "$($SPACK location -i fdmnes)/bin/fdmnes" "$HOME/.local/bin/fdmnes"
```

It needs a C and Fortran compiler (gcc and gfortran). If `compiler find` finds no Fortran
compiler, say so: installing one needs the system's package manager (for example
`apt-get install gfortran`, which needs administrator rights; CLIO asks the person before
running a command outside the sandbox) or conda (`conda install -c conda-forge
gfortran`). Run long builds with progress visible; a failed build keeps its log in the
stage folder: read it and report the error.

FDMNES's source link always holds its newest revision, so the recipe's checksum fails
after FDMNES releases a new one. Report that error as it is; do not bypass the checksum.

## Check

Call `fdmnes_status`: it finds the program with no setting. Then run the calculation again.
