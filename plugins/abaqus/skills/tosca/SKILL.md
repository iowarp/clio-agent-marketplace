---
name: tosca
title: Set Up and Read a Tosca Optimization Run
description: Use for Tosca Structure optimization (topology, sizing, shape, bead) driven by a .par file - its inputs, outputs and documentation lookups; load with topology-optimization and abaqus.
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

The `.par` command syntax is not reproduced here. It lives in the Tosca
documentation of the installed release; syntax recalled from memory can be
another release's: how the design
area, design variables, objective, constraints, manufacturing restrictions,
stop criteria and smoothing are declared, and how a run is launched. A text
conversion of the manual can be searched per keyword. A working `.par` file
the scientist supplies from an earlier study is a tested starting point; the
new formulation decides what differs.

## What a run takes

- A task type: topology, sizing, shape or bead.
- A referenced Abaqus input deck. An optimization failure is a Tosca problem
  only once that deck runs and converges on its own.
- The design area, frozen regions, symmetry and every manufacturing
  restriction the study needs, declared inside the `.par` file. A restriction
  stated in prose does not constrain the optimizer.
- The `.par` file's smoothing level (`ISO_VALUE`): every later view and
  extracted surface depends on it.

## What a run writes

These outputs are used by `visualize-topology-optimization` and
`abaqus-visualization`; their names can differ between releases and setups,
so the run directory is the reference:

- `optimization_report.csv`: objective and constraints per design cycle, with
  a `Norm-Values` row Tosca uses to normalize them;
- per-cycle Abaqus results, which `mdb.CombineOptResults` (inside
  `abaqus cae noGUI=...`) merges into one ODB with one frame per cycle and the
  element density as `MAT_PROP_NORMALIZED`;
- `TOSCA_POST/ISO_SMOOTHING.stl`: the smoothed surface at `ISO_VALUE`;
- re-analysis models of the final design when the run requests them (for
  example under `SAVE.inp/<cycle>/`).

## After a run

The convergence history from `optimization_report.csv` is a separate question
from the manufacturability check and the structural re-verification of the
extracted geometry (`topology-optimization`, "The result is a proposal"). Tosca evaluates its
own stress responses on the density-penalized model, so peak stresses read
from the smoothed surface are not proof that a stress constraint held.

Without executed solver evidence the package is `GENERATED_NOT_EXECUTED`.
