---
name: install-graspa
description: When the gRASPA connector reports binary_missing, decide with the person where gRASPA will run - a GPU node of a cluster (build it there with Spack and run prepared folders through Slurm) or this machine if it has an NVIDIA or AMD GPU - or go on with prepared folders only.
keywords: [graspa, gpu, spack, slurm, install, level:L2]
---

# Get gRASPA, or run it elsewhere

gRASPA runs only on a GPU: NVIDIA (built with the NVIDIA HPC SDK) or AMD (built with
ROCm/HIP). The gRASPA connector never downloads or builds it. Without it here,
`prepare_graspa` still writes complete run folders and `read_graspa` reads them back.

## Where gRASPA may already be

`binary_missing` means only that the connector found no gRASPA where it looks: its **gRASPA
program** value and `nvc_main.x`, `hip_main.x`, `graspa` or `sycl.out` on PATH. On a machine
with a GPU, gRASPA may be elsewhere: a Spack install (`spack find -p graspa`), a module
(`module avail graspa`), or a build folder. Using one found there is the person's choice
(`ask_user`, naming its path). **gRASPA program** (`graspa`) set with `set_connector_value`
lets `run_graspa` use it; the value belongs to this conversation, and the gRASPA
connector's settings hold a saved default.

## Where it runs

Where gRASPA runs is the person's decision (`ask_user`):

- **a cluster GPU node**: build gRASPA there and submit the prepared folders (below);
- **this machine** (only if it has a GPU: `nvidia-smi` or `rocm-smi` shows it);
- **prepare the folders only**: the person runs them, and the results stay unverified
  until they do.

## Build with Spack, in one folder

On the machine that has the GPU (through relay's site for a cluster), with
everything Spack writes under one folder (see the fdmnes plugin's `install-fdmnes` for
the same environment variables, or clio-kit's `spack-repo/README.md`):

```sh
$SPACK install graspa +cuda                         # NVIDIA: pulls the NVIDIA HPC SDK
$SPACK install graspa +rocm amdgpu_target=gfx90a    # AMD: set the GPU architecture
$SPACK location -i graspa                           # bin/nvc_main.x or bin/hip_main.x
```

On a cluster, the site's modules provide the compilers (`module load nvhpc` or `rocm`),
and `spack external find` tells Spack about them; sites that forbid long builds on login
nodes need the build on a compute node. The NVIDIA HPC SDK is a large download (several
GB).

## Running prepared folders on a GPU node

Each folder from `prepare_graspa` runs with its gRASPA executable, standard output
saved as `graspa_stdout.txt`, in that folder:

```sh
cd <run folder> && <path>/nvc_main.x > graspa_stdout.txt
```

They run as Slurm jobs (one per folder, or an array) with a GPU requested; folders that
ran on another file system need copying back before `read_graspa` reads each one. Where
gRASPA was built on this machine, **gRASPA program** points at it as above.
