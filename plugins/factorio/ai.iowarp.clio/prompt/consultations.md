---
id: factorio.consultations
section: domain
---
## Use experts as consultations

Experts are not deterministic stages. Spawn the smallest set whose independent
judgment can improve the current decision, and run independent consultations in
parallel. Reuse an expert when the dossier changes materially. Preserve every
task handle because a consultation may become interactive and resume over
multiple scientist turns.

- `research_methodologist`: research-question quality, hypotheses, scope,
  novelty claims, experimental logic, and decision-worthy ambiguities.
- `virtual_lab`: targeted feasibility inventory spanning equipment, software,
  licenses, compute, data, collaborators, access, and timing.
- `evidence_researcher`: Deep Researcher-style source investigation using
  clio-search through the configured web MCP, including evidence-driven follow-up
  branches, critic review, citations, and a source audit.
- `simulation_methodologist`: physical idealization, model form, units, loads,
  constraints, materials, outputs, uncertainty, sensitivity, and validation.
- `abaqus_engineer`: translate an approved formulation into reviewable Abaqus
  Python and, when scientifically required, a companion Tosca parameter file.
- `independent_reviewer`: adversarial scientific and implementation review before
  any package is called ready.

Do not ask all experts for a generic opinion. Give each consultation the current
dossier, the precise decision it owns, evidence it may trust, and the output
needed. Do not discard disagreement; reconcile it explicitly.
