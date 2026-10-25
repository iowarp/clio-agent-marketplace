---
name: tosca
title: Set Up and Read a Tosca Optimization Run
description: Tosca Structure, the SIMULIA optimization module that drives Abaqus solves from a .par parameter file (topology, sizing, shape and bead optimization). What it needs, what it writes, and what to look up in the installed documentation. Load with topology-optimization and abaqus.
keywords:
- level:L2
- abaqus
- tosca
- topology-optimization
---

Tosca Structure wraps an Abaqus model in an optimization loop: each design
cycle it updates the design variables, runs an Abaqus solve and reads the
responses. The method (stating the problem, checking the baseline model,
reading the result as a proposal) is in `topology-optimization`; the Abaqus
model and runs are in `abaqus`. This skill holds only what is specific to
Tosca.

## What this skill does not supply

The `.par` command syntax is not reproduced here. Read it from the Tosca
documentation of the installed release, never from memory: how the design
area, design variables, objective, constraints, manufacturing restrictions,
stop criteria and smoothing are declared, and how a run is launched. Convert
the manual to text once and search it for each keyword you need. When the
scientist supplies a working `.par` file from an earlier study, start from it
and change only what the new formulation requires.

## Before a run

- Choose the task type: topology, sizing, shape or bead.
- Confirm the referenced Abaqus input deck runs on its own and converges
  before treating any optimization failure as a Tosca problem.
- Declare the design area, frozen regions, symmetry and every manufacturing
  restriction the study needs inside the `.par` file. A restriction stated in
  prose does not constrain the optimizer.
- Record the `.par` file's smoothing level (`ISO_VALUE`): every later view and
  extracted surface depends on it.

## What a run writes

These outputs are used by `visualize-topology-optimization` and
`abaqus-visualization`; confirm the names in the run directory, since they
can differ between releases and setups:

- `optimization_report.csv`: objective and constraints per design cycle, with
  a `Norm-Values` row Tosca uses to normalize them;
- per-cycle Abaqus results, which `mdb.CombineOptResults` (inside
  `abaqus cae noGUI=...`) merges into one ODB with one frame per cycle and the
  element density as `MAT_PROP_NORMALIZED`;
- `TOSCA_POST/ISO_SMOOTHING.stl`: the smoothed surface at `ISO_VALUE`;
- re-analysis models of the final design when the run requests them (for
  example under `SAVE.inp/<cycle>/`).

## After a run

Track the convergence history from `optimization_report.csv` separately from
the manufacturability check and the structural re-verification of the
extracted geometry (`topology-optimization`, section 4). Tosca evaluates its
own stress responses on the density-penalized model, so peak stresses read
from the smoothed surface are not proof that a stress constraint held.

Return the `.par` file and the Abaqus deck it references, the declared
regions and restrictions, the run's stop reason and convergence history, and
traceability to the approved formulation. Without executed solver evidence
the package is `GENERATED_NOT_EXECUTED`.
