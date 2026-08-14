---
name: formulate_abaqus_package
title: Formulate an Abaqus Package
description: Turn an approved scientific question into an auditable simulation specification and generated Abaqus/Tosca handoff with explicit assumptions, validation, and execution status.
---

Use this skill before and during Abaqus authoring. Ensure the package traces one
continuous argument:

```text
research question
-> quantity of interest
-> physical idealization
-> geometry, material, loads, constraints, and interactions
-> discretization and solver procedure
-> requested outputs
-> validation/sensitivity evidence
-> scientific conclusion the outputs may support
```

Do not treat boundary conditions, material law, optimization objective, or
validation as code-generation details. Obtain explicit decisions for choices
that change the physical claim. Low-risk numerical defaults may be proposed with
justification and a plan to test sensitivity.

Every generated package declares units, target Abaqus release and interpreter,
license/module assumptions, external inputs, run command, expected outputs,
verification checklist, and truthful execution status. A package that has not
run is `GENERATED_NOT_EXECUTED` regardless of how plausible the code looks.

