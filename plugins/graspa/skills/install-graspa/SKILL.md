---
name: install-graspa
description: When the gRASPA connector reports binary_missing, decide with the person where gRASPA will run - a GPU node of a cluster (build it there with Spack and run prepared folders through Slurm) or this machine if it has an NVIDIA or AMD GPU - or go on with prepared folders only.
keywords: [graspa, gpu, spack, slurm, install, level:L2]
---

# Get gRASPA, or run it elsewhere

gRASPA runs only on a GPU: NVIDIA (built with the NVIDIA HPC SDK) or AMD (built with
ROCm/HIP). The gRASPA connector never downloads or builds it. Without it here,
`prepare_graspa` still writes complete run folders and `read_graspa` reads them back.

## Ask where it runs

Ask once with `ask_user`:

- **a cluster GPU node**: build gRASPA there and submit the prepared folders (below);
- **this machine** (only if it has a GPU: check `nvidia-smi` or `rocm-smi`);
- **prepare the folders only**: the person runs them; say what stays unverified.

## Build with Spack, in one folder

On the machine that has the GPU (through the ssh and slurm tools for a cluster), with
everything Spack writes under one folder (see the fdmnes plugin's `install-fdmnes` for
the same environment variables, or clio-kit's `spack-repo/README.md`):

```sh
$SPACK install graspa +cuda                         # NVIDIA: pulls the NVIDIA HPC SDK
$SPACK install graspa +rocm amdgpu_target=gfx90a    # AMD: set the GPU architecture
$SPACK location -i graspa                           # bin/nvc_main.x or bin/hip_main.x
```

On a cluster, prefer the site's modules for the compilers (`module load nvhpc` or
`rocm`) and tell Spack about them (`spack external find`), and build on a compute node
if login nodes forbid long builds. The NVIDIA HPC SDK is a large download (several GB):
say so before starting.

## Running prepared folders on a GPU node

Each folder from `prepare_graspa` runs with its gRASPA executable, standard output
saved as `graspa_stdout.txt`, in that folder:

```sh
cd <run folder> && <path>/nvc_main.x > graspa_stdout.txt
```

Submit them as Slurm jobs (one per folder, or an array) with a GPU requested, copy the
folders back if they ran on another file system, then `read_graspa` each one. Where
gRASPA runs on this machine, set the connector's **gRASPA program** value to it and use
`run_graspa`.
