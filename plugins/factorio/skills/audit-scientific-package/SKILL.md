---
name: audit-scientific-package
title: Audit a Scientific Simulation Package
description: Use to review a research or simulation package from its actual files, returning severity-ranked, evidence-linked findings and a readiness verdict.
keywords:
- level:L1
- factorio
- review
---

A package is what its files say, not what a summary of them says: the study
log (`query_log`), cited sources, specification and generated files. Some
checks are cheap to run (a script parses, a deck references only files that
exist, the solver's status file says the run completed). A claim holds when
the question traces through evidence, decisions, formulation, implementation,
expected outputs, validation and the claim the scientist intends to make.

Five linked surfaces can fail:

- **Evidence**: citations were read and support bounded claims; parameter
  values have a source; contrary evidence and search limits are visible.
- **Physics**: units, magnitudes, signs, conservation, constitutive
  behavior, geometry and load path, supports, contacts, singularities, and
  limiting behavior are plausible; optimization responses and regions match
  the formulation.
- **Traceability**: major model and code choices map to accepted decisions
  or explicit proposals.
- **Construction**: files are complete for the target interpreter and
  program release, with no hidden placeholders, undefined references or
  invented inputs.
- **Validation**: convergence, sensitivity, analytical or experimental
  benchmarks and acceptance criteria can test the intended claim, and the
  artifact status is truthful.

A finding is useful with its severity, the evidence (file and location), its
impact on the claim, and which specialist or decision owns the fix. An
unresolved scientist-owned decision is a finding, not a question the reviewer
answers.

`REVISION_REQUIRED` marks a material defect; `READY_FOR_SCIENTIST_REVIEW`
means the package is coherent and its remaining limitations are explicit.
Readiness never means solver-verified: generated files are executed or
validated only when run artifacts show it.
