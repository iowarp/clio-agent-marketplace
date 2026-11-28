---
name: install-fdmnes
description: When the FDMNES connector reports binary_missing (no FDMNES program), build FDMNES with Spack in a folder of its own with the person's consent, point the connector at it, or go on without computing spectra when the person declines; Linux and macOS.
keywords: [fdmnes, spack, install, level:L2]
---

# Get FDMNES, or go on without it

The FDMNES connector runs an FDMNES program already on the machine and never downloads
one. Reading, normalizing and comparing spectra work without it; only `run_xanes` needs it.

## Where FDMNES may already be

`binary_missing` means only that the connector found no FDMNES where it looks: its **FDMNES
program** value and `fdmnes` or `fdmnes_linux` on PATH. FDMNES may be elsewhere: a Spack
install (`spack find -p fdmnes`, or this skill's own `~/.local/opt/clio-spack`), a cluster
module (`module avail fdmnes`), or an unpacked download in another folder. Using one found
there is the person's choice (`ask_user`, naming its path). **FDMNES program** (`fdmnes`)
set with `set_connector_value` belongs to this conversation; the FDMNES connector's
settings hold a saved default.

## The person's choice

Installing is the person's decision (`ask_user`, a choice): **build it now** (about a
minute to compile, a few more the first time Spack builds its maths libraries, under 1 GB
in one folder), **I'll install it myself** (with the steps), or **skip computing
spectra** (spectra then stay uncomputed). A declined build stays declined for the
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

It needs a C and Fortran compiler (gcc and gfortran). When `compiler find` finds no
Fortran compiler, one comes from the system's package manager (for example
`apt-get install gfortran`, which needs administrator rights; CLIO asks the person before
running a command outside the sandbox) or conda (`conda install -c conda-forge
gfortran`). Long builds can run with progress visible; a failed build keeps its log in the
stage folder, with the error.

FDMNES's source link always holds its newest revision, so the recipe's checksum fails
after FDMNES releases a new one. That error is what it says; do not bypass the checksum.

## Check

`fdmnes_status` finds the program with no setting.
