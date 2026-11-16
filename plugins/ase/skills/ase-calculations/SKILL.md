---
name: ase-calculations
title: Calculations with ASE
description: Use when a molecule's structure, energy, optimized geometry, vibrations, thermochemistry or IR spectrum is to be computed with the ASE connector, or a structure is to be built from SMILES, measured, or changed (a bond, angle or dihedral) before a calculation.
keywords: [ase, xtb, mace, uma, nwchem, orca, optimization, frequencies, level:L2]
---

# Calculations with the ASE connector

Structures travel as files. Every tool takes a structure file (XYZ, SDF/MOL, PDB, CIF,
ASE .traj, POSCAR) and returns a `structure` record (path, formula, atom count, hash) for
each file it writes; calculations also return `results_file` (result.json). Outputs land in
the workspace under `chemistry/ase/`; nothing is overwritten. Pass paths from one tool to
the next; do not retype coordinates.

## Tools and when

| Need | Tool |
| --- | --- |
| A 3D structure from SMILES | `smiles_to_structure` (RDKit embedding and force-field relaxation; it names unassigned stereocentres) |
| Formula, bonds, distances, angles, dihedrals | `inspect_structure` with `measure` (0-based atom indices in file order) |
| A distance, angle or dihedral set to a value | `set_geometry` (moves the smaller fragment; refuses ring bonds) |
| Energy, optimization, frequencies, thermochemistry, IR | `run_ase` with `driver` energy, opt, vib, thermo or ir |
| Leave a saddle point, or start from a mode | `displace_along_mode` (from result.json, its normal_modes.npz or a mode animation) |
| Restart from an optimization step | `trajectory_frame` |
| Which calculators work here | `calculators` |

## run_ase

- `calculator`: `{type: 'xtb'}` (GFN2-xTB), `{type: 'mace'}` (MACE-OFF23 small),
  `{type: 'uma'}`, `{type: 'nwchem', method, basis}`, `{type: 'orca', method, basis}`;
  `emt` only for tests. Choose with the `method-ladder` skill.
- `charge` and `multiplicity` go to the calculator and the thermochemistry; the result
  notes when a calculator ignores them.
- `constraints` hold atoms, bonds, angles or dihedrals during an optimization (a value
  given is set first). Frequencies always use the full Hessian, so a constrained
  optimization followed by `vib` gives the saddle point and its imaginary mode in one call.
- `optimize: false` runs vib, thermo or ir on the structure as given.
- Files in the run folder: `final.xyz`, `opt_trajectory.xyz` and `opt_steps.csv` (a chart
  of energy and force per step, linked to the trajectory frames), `frequencies.csv`,
  `modes/mode_NNN.xyz` (one animation per mode), IR CSVs, `result.json`.

Then check the result with `geometry-and-frequencies`. Show structures, trajectories and
modes in the Burette viewer when it is enabled (`open_structure`, `play_mode`).

## First use and missing programs

xTB, MACE and UMA build their environment the first time they are used (seconds to
minutes; progress is reported). `calculators` says what is ready. A typed error names
what is missing:

- `binary_missing` for NWChem or ORCA: use the nwchem or orca plugin's skill, or pick a
  calculator that is ready and say so.
- `hf_token_missing`: UMA needs a Hugging Face token whose account accepted the UMA
  licence, set in the connector's **Hugging Face token (UMA)** value. Ask the person; do
  not look for another way.
- `dipole_unavailable`: IR needs xtb, nwchem or orca.
