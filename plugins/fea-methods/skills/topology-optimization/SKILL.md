---
name: topology-optimization
title: Formulate, Run and Interpret a Topology Optimization Study
description: State the optimization problem precisely (objective, constraints, design and frozen regions, manufacturing restrictions), check the analysis model before blaming the optimizer, and treat the converged result as a design proposal that still needs re-verification. Program-independent; the program plugin supplies the syntax.
keywords:
- level:L1
- topology-optimization
- simulation
---

This skill is the method. The program plugin the scientist works in (for
example a Tosca or a Morphorm skill) supplies the input syntax, run commands
and output files; load it alongside this one.

## 1. State the problem before writing any input

- **Objective**: minimize compliance, maximize stiffness per mass, minimize
  mass or volume under a stress constraint, or another stated response.
- **Constraints**: volume or mass fraction, stress, displacement, frequency.
  Say which response each constraint is evaluated on and where (a stress
  constraint over a region, a displacement at a named point).
- **Regions**: the design region, and the frozen (non-design) regions that
  must keep material: load introduction, supports, interfaces, machined faces.
- **Restrictions applied inside the optimization**: symmetry, extrusion or
  rotation, minimum member size, overhang angle for additive builds, casting
  or milling directions.
- **Load cases** and how they combine (weighted sum, worst case).

Record each of these as a decision with its owner. A restriction stated only
in prose does not constrain the optimizer: it must appear in the program's own
input, and the generated configuration should be checked to confirm it did.

## 2. Check the analysis model first

The optimizer repeats an ordinary finite-element analysis. Before any
optimization run, solve the baseline model on its own (`finite-element-analysis`,
`meshing`, `boundary-conditions`) and confirm it is valid: loads and supports
represent the real part, the mesh resolves the regions the objective and
constraints read, and the baseline responses are plausible. A failure of the
baseline is not an optimizer failure.

## 3. Run and track convergence

Track the optimizer's own history: objective and each constraint per design
cycle, the cycle count and the stop reason. Normalize each quantity to its
start value or limit when plotting them together. Converged means the
optimizer met its own stop criterion under its stated problem, nothing more.

## 4. Interpret the result as a proposal

Three questions stay separate, whatever program produced the topology:

1. **Did the optimizer converge?** Section 3 answers only this.
2. **Can the geometry be made?** Check the extracted geometry against the
   process constraints (`manufacturability`). A restriction applied after the
   optimization, by hand or in a second step, changes the converged topology,
   so the result needs re-verification.
3. **Does the part perform?** Extract a smooth geometry at a stated density
   threshold, remesh it cleanly, and re-run the structural check outside the
   optimization loop. The optimizer's stresses come from a density-penalized
   model and are not proof that a stress constraint holds on the real part.

Watch the extraction: a threshold that leaves only frozen regions, or pieces
with no material between them, means the threshold or the cycle is wrong.
Report that as a finding instead of presenting a disconnected part.

## Return

The problem statement (objective, constraints, regions, restrictions, load
cases), the converged result with its constraint satisfaction and stop reason,
the manufacturability check, the re-verification status, and traceability to
the approved formulation. Without executed solver evidence the result is
labelled `GENERATED_NOT_EXECUTED`.
