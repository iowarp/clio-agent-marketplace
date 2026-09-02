---
id: factorio-flat
title: Factorio Flat
display_name: Factorio Flat
version: 0.1.0
description: A scientist-facing research partner with a small permanent identity prompt, focused specialist consultations, on-demand coordination skills, evidence fan-out, and reviewable Abaqus handoffs.
root_expert: main
blueprint:
  format: agent-blueprint-v1
mcp_servers:
  web: clio-kit mcp-server web
experts:
  - experts/main.md
  - experts/research_methodologist.md
  - experts/virtual_lab.md
  - experts/evidence_researcher.md
  - experts/evidence_leaf.md
  - experts/evidence_critic.md
  - experts/simulation_methodologist.md
  - experts/abaqus_engineer.md
  - experts/independent_reviewer.md
defaults:
  prompt_profile: heavy
---

# Factorio Flat

Factorio Flat keeps the scientist-facing identity and scientific integrity of
Factorio while moving task-specific methods and coordination mechanics into
skills that are loaded only when relevant. It declares no fixed workflow: the
current scientific question determines whether the root answers directly, asks
for a consequential clarification, loads a procedure, consults one specialist,
or coordinates independent investigations.

The first delivery boundary remains a traceable research dossier, defensible
simulation specification, reviewable Abaqus/Tosca package when applicable, and
truthful verification state. Solver execution is outside this pack until a real
execution tool returns evidence.
