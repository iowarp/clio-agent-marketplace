---
name: audit-scientific-package
title: Audit a Scientific Simulation Package
description: Review a research and simulation package across evidence, physics, traceability, construction and validation by reading the actual files, and return severity-ranked, evidence-linked findings with a readiness verdict that never claims solver verification it does not have.
keywords:
- level:L1
- factorio
- review
---

Read the actual dossier, cited sources, specification and generated files;
open them, do not review a summary of them. Where a check can be run cheaply
(a script parses, a deck references only files that exist, the solver's
status file says the run completed), run it. Trace the question through
evidence, decisions, formulation, implementation, expected outputs,
validation and the claim the scientist intends to make.

Audit five linked surfaces:

1. **Evidence**: citations were read and support bounded claims; parameter
   values have a source; contrary evidence and search limits are visible.
2. **Physics**: units, magnitudes, signs, conservation, constitutive
   behavior, geometry and load path, supports, contacts, singularities, and
   limiting behavior are plausible; optimization responses and regions match
   the formulation.
3. **Traceability**: major model and code choices map to accepted decisions
   or explicit proposals.
4. **Construction**: files are complete for the target interpreter and
   program release, with no hidden placeholders, undefined references or
   invented inputs.
5. **Validation**: convergence, sensitivity, analytical or experimental
   benchmarks and acceptance criteria can test the intended claim, and the
   artifact status is truthful.

Report each finding with severity, the evidence (file and location), its
impact on the claim, and which specialist or decision owns the fix. An
unresolved scientist-owned decision is a finding, not a question you answer.

Verdict: `REVISION_REQUIRED` for any material defect;
`READY_FOR_SCIENTIST_REVIEW` only when the package is coherent and its
remaining limitations are explicit. Readiness never means solver-verified:
never upgrade generated files to executed or validated without the run
artifacts that show it.
