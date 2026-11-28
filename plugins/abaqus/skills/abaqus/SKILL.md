---
name: abaqus
title: Script, Run and Audit an Abaqus Package
description: Use for Abaqus/Standard, Abaqus/Explicit or Abaqus/CAE scripting work - building a complete package from an approved formulation, running it when Abaqus is reachable, and reporting what ran.
keywords:
- level:L2
- abaqus
- simulation
---

Abaqus is one program a study can use, not the default; it fits a scientist
who works in it or asks for it. The method behind each modelling choice
is in `finite-element-analysis`, `meshing`, `boundary-conditions` and
`stress-strain-analysis`; this skill covers how Abaqus carries it out.

## The target environment

What a package depends on:

- the Abaqus release, and so the scripting interpreter: older releases embed
  Python 2, newer ones Python 3. Code for the wrong one fails to run. The
  installation reports its release (for example `abaqus information=release`);
- the solver (Standard or Explicit), add-on modules (CAE, Tosca, CAD
  associative interfaces) and the licence they need;
- the unit system. Abaqus has none of its own: every input must use one
  consistent set, stated in the package;
- where it runs: this machine, a remote workstation, or a cluster with a
  batch scheduler.

## The complete chain

Part geometry or import; material and section assignment; assembly; steps and
procedures; interactions, contact and constraints; loads and boundary
conditions; mesh with element type stated; field and history output requests;
job definition and input generation; requested post-processing.

- Stable named sets and surfaces keep the model editable and auditable;
  positional or picked references break when the geometry changes.
- Abaqus/CAE's native optimization objects and a Tosca `.par`-driven
  workflow are different mechanisms, even when both are called topology
  optimization inside Abaqus; a package reads correctly when it names which
  one it uses. `tosca` covers the Tosca one.
- Scientist-owned choices trace to an accepted decision; a numerical default
  the agent proposes is recognisable as one when labelled.

A ready package has no TODOs, ellipses, undefined names, invented files or
hidden inputs.

## Running it

With Abaqus reachable, a package can run here instead of being handed over
as files. Scripts written to files run through the shell:
`abaqus cae noGUI=SCRIPT.py` builds a model and its input deck from
a CAE script, `abaqus python SCRIPT.py` runs post-processing against an ODB,
and `abaqus job=NAME input=DECK.inp` submits a deck. The exact options are in
the installed release's documentation. `hpc-batch-jobs` covers submission and
bounded waits on a batch cluster.

A job's `.sta`, `.msg` and `.dat` files are the evidence behind any result:
the status file states whether the analysis completed, and errors
and warnings are reported in the others. A job that wrote an ODB can still
have failed to converge in a later increment.

## What a package declares

A package is readable on its own when it states its units, target release
and interpreter, licence and module assumptions, external inputs, run
commands, expected outputs, traceability to the approved formulation, and the
verification checks run on it. Its status is one of:

- `GENERATED_NOT_EXECUTED`: files written, no solver run in this session;
- `SOLVER_EXECUTED`: the run finished and its status and message files were
  read; name the files;
- `VALIDATED`: compared against a stated benchmark with its acceptance
  criterion.

Each status rests on the files that support it.

`abaqus-visualization` shows geometry and results.
