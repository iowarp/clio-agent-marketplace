---
name: audit_scientific_package
title: Audit a Scientific Simulation Package
description: Apply citation-integrity, physical-sanity, runnable-by-construction, traceability, and validation review without replacing scientific judgment with a deterministic score.
---

Use this skill before Factorio presents a simulation package as ready for the
scientist. Read the actual dossier, sources, specification, and generated files.

Audit five linked surfaces:

1. Evidence: every material citation was read and supports its claim; contrary
   evidence and search boundaries are visible.
2. Physics: units, magnitudes, conservation, constitutive behavior, load path,
   constraints, and expected limiting behavior are plausible.
3. Traceability: each major model/code choice maps to an accepted decision or an
   explicitly marked proposal.
4. Construction: scripts are complete for their declared interpreter and contain
   no hidden placeholders, undefined references, or invented external artifacts.
5. Validation: convergence, sensitivity, analytical/experimental benchmarks, and
   acceptance criteria can test the intended claim.

Report concrete findings with severity and evidence. Do not let a checklist vote
away a scientific contradiction. Never upgrade generated code to executed or
validated without real solver artifacts.

