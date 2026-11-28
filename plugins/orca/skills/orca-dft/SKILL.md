---
name: orca-dft
description: Use when a DFT calculation is to be run with ORCA through the ASE connector's orca calculator - choosing functional, basis set, spin and parallel runs. Not tested without an ORCA install.
keywords: [orca, dft, functional, basis set, level:L2]
---

# DFT with ORCA through the ASE connector

ORCA works only after the person installed it (`install-orca`). This plugin has not been
run against a real ORCA here, which the person does not know unless told.

`run_ase` with `calculator: {type: 'orca', method: <functional>, basis: <basis>}`.
Defaults are B3LYP and def2-SVP. ORCA's simple input line takes the method and basis
together, and the `blocks` setting adds `%` blocks.

- **Dispersion:** D3BJ or D4 on the method line matters for conformers and non-covalent work.
- **Speed:** RIJCOSX with an auxiliary basis (def2/J) speeds up hybrid functionals.
- **Charge and spin:** `charge` and `multiplicity` go to the `* xyz` line; open shells run
  unrestricted (UKS).
- **Parallel runs:** `nprocs` adds a `%pal` block; ORCA must then be called by its full
  path and Open MPI must be on PATH.

ORCA's output is in the run folder, where a failed run explains itself.
