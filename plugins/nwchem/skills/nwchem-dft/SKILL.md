---
name: nwchem-dft
description: Use when a DFT or Hartree-Fock calculation is to be run with NWChem through the ASE connector's nwchem calculator - choosing the functional, basis set, spin and parallel launch, and reading what NWChem reports.
keywords: [nwchem, dft, functional, basis set, mpi, level:L2]
---

# DFT with NWChem through the ASE connector

`run_ase` with `calculator: {type: 'nwchem', method: <functional>, basis: <basis>}`.
Defaults are B3LYP and 6-31G*. Choose them with `method-ladder`.

- **Functional and dispersion:** for non-covalent interactions or conformers add a
  dispersion correction (for example a functional with a built-in correction, or a
  `blocks` entry `dft: {disp: {vdw: 3}}`); say which.
- **Basis:** 6-31G* or def2-SVP for geometries; def2-TZVP for energies when time allows.
  Anions need diffuse functions (6-31+G*).
- **Charge and spin:** `charge` and `multiplicity` go to NWChem (`mult` for DFT, `nopen`
  for HF-based theories). An open-shell species runs unrestricted; check the reported
  ⟨S²⟩ for spin contamination when NWChem prints it.
- **Parallel runs:** the calculator setting `nprocs` launches with `mpirun -np N`; use the
  machine's cores, not more.
- **Time:** DFT frequencies are the expensive step (finite differences, 6N gradients).
  For a large molecule optimize with DFT and say whether frequencies came from a cheaper
  level.

NWChem's own output is in the run folder (the calculator's `.nwo`); read it when a run
fails or an SCF does not converge. When NWChem is not installed, use `install-nwchem`.
