---
name: topology-optimization
title: Formulate, Run and Interpret a Topology Optimization Study
description: Use for topology optimization in any program, to state the problem precisely, check the analysis model, and treat the converged result as a design that still needs re-verification.
keywords:
- level:L1
- topology-optimization
- simulation
---

This skill is the method. The program plugin the scientist works in (for
example a Tosca or a Morphorm skill) supplies the input syntax, run commands
and output files.

## The problem

- **Objective**: minimize compliance, maximize stiffness per mass, minimize
  mass or volume under a stress constraint, or another stated response.
- **Constraints**: volume or mass fraction, stress, displacement, frequency.
  Each constraint is evaluated on a response and somewhere (a stress
  constraint over a region, a displacement at a named point).
- **Regions**: the design region, and the frozen (non-design) regions that
  keep material: load introduction, supports, interfaces, machined faces.
- **Restrictions applied inside the optimization**: symmetry, extrusion or
  rotation, minimum member size, overhang angle for additive builds, casting
  or milling directions.
- **Load cases** and how they combine (weighted sum, worst case).

Each of these is a decision with an owner. A restriction stated only in prose
does not constrain the optimizer: it constrains only once it appears in the
program's own input, which the generated configuration shows.

## The analysis model underneath

The optimizer repeats an ordinary finite-element analysis. The baseline model
solved on its own (`finite-element-analysis`, `meshing`,
`boundary-conditions`) shows whether loads and supports represent the real
part, the mesh resolves the regions the objective and constraints read, and
the baseline responses are plausible. A failure of the baseline is not an
optimizer failure.

## Convergence

The optimizer's own history is the objective and each constraint per design
cycle, the cycle count and the stop reason; plotted together, each quantity
reads best normalized to its start value or limit. Converged means the
optimizer met its own stop criterion under its stated problem, nothing more.

## The result is a proposal

Three questions stay separate, whatever program produced the topology:

- **Did the optimizer converge?** The history answers only this.
- **Can the geometry be made?** The extracted geometry meets the process
  constraints (`manufacturability`) or not. A restriction applied after the
  optimization, by hand or in a second step, changes the converged topology,
  so the result needs re-verification.
- **Does the part perform?** A smooth geometry extracted at a stated density
  threshold, remeshed cleanly and re-run outside the optimization loop,
  answers it. The optimizer's stresses come from a density-penalized model and
  are not proof that a stress constraint holds on the real part.

A threshold that leaves only frozen regions, or pieces with no material
between them, means the threshold or the cycle is wrong; that is a finding,
not a disconnected part. A result without executed solver evidence is
`GENERATED_NOT_EXECUTED`.
