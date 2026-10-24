---
name: abaqus
title: Script, Run and Audit an Abaqus Package
description: Turn an approved simulation formulation into a complete Abaqus package (Python scripts or input decks), run it when Abaqus is reachable, and report exactly what was generated, executed and checked. Load for any Abaqus/Standard, Abaqus/Explicit or Abaqus/CAE scripting work.
keywords:
- level:L2
- abaqus
- simulation
---

Abaqus is one program a study can use, not the default. Use it when the
scientist works in it or asks for it. The method behind each modelling choice
is in `finite-element-analysis`, `meshing`, `boundary-conditions` and
`stress-strain-analysis`; this skill covers how Abaqus carries it out.

## 1. Pin the target environment

Before writing a line, establish and record:

- the Abaqus release, and so the scripting interpreter: older releases embed
  Python 2, newer ones Python 3. Code for the wrong one fails to run. Ask or
  check the installation (for example `abaqus information=release`) rather
  than assume;
- the solver (Standard or Explicit), add-on modules (CAE, Tosca, CAD
  associative interfaces) and the licence they need;
- the unit system. Abaqus has none of its own: every input must use one
  consistent set, stated in the package;
- where it runs: this machine, a remote workstation, or a cluster with a
  batch scheduler.

## 2. Build the complete chain

Part geometry or import; material and section assignment; assembly; steps and
procedures; interactions, contact and constraints; loads and boundary
conditions; mesh with element type stated; field and history output requests;
job definition and input generation; requested post-processing.

- Use stable named sets and surfaces, never positional or picked references,
  so the model stays editable and auditable.
- Abaqus/CAE's native optimization objects and a Tosca `.par`-driven
  workflow are different mechanisms, even when both are called topology
  optimization inside Abaqus. Name which one the package uses; for Tosca,
  load `tosca`.
- Make every scientist-owned choice traceable to an accepted decision.
  Safe numerical defaults may be proposed, labelled as such.

A ready package has no TODOs, ellipses, undefined names, invented files or
hidden inputs.

## 3. Run it when you can

When Abaqus is reachable and the scientist wants results, run the package
rather than handing over files. Write scripts to files and run them through
the shell: `abaqus cae noGUI=SCRIPT.py` builds a model and its input deck from
a CAE script, `abaqus python SCRIPT.py` runs post-processing against an ODB,
and `abaqus job=NAME input=DECK.inp` submits a deck. Check the exact options
in the installed release's documentation. On a batch cluster, load
`hpc-batch-jobs` for submission and bounded waits.

After a run, read the job's `.sta`, `.msg` and `.dat` files before quoting
any result: the status file states whether the analysis completed, and errors
and warnings are reported in the others. A job that wrote an ODB can still
have failed to converge in a later increment.

## 4. Declare the package

Every package states: units; target release and interpreter; licence and
module assumptions; external inputs; run commands; expected outputs;
traceability to the approved formulation; and the verification checks run on
it. Status is one of:

- `GENERATED_NOT_EXECUTED`: files written, no solver run in this session;
- `SOLVER_EXECUTED`: the run finished and its status and message files were
  read; name the files;
- `VALIDATED`: compared against a stated benchmark with its acceptance
  criterion.

Never upgrade a status without the files that support it.

## Return

The exact file content or paths, the manifest, the environment assumptions,
the run commands, what was executed and its outcome, the expected or produced
outputs, and the checks still open. To show geometry or results, load
`abaqus-visualization`.
