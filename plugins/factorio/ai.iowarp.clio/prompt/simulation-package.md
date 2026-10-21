---
id: factorio.simulation-package
section: domain
---
## From idea to simulation package

Plans are executable scientific specifications, not project-management prose.
Before asking `abaqus_engineer` to author a ready script, obtain scientist approval
for the material decisions that determine the model, including as applicable:

- geometry/design domain and coordinate system;
- unit system;
- material law and source of parameters;
- analysis procedure and physical idealizations;
- interactions, boundary conditions, and loads;
- mesh strategy and convergence evidence required;
- topology/shape objective, constraints, design and frozen regions;
- requested field/history outputs;
- validation benchmarks, sensitivity checks, and acceptance criteria;
- Abaqus release, license/Tosca availability, and execution environment.

The formulation may be static, modal, buckling, dynamic/explicit, thermal,
coupled, contact, fracture, fatigue, topology/shape optimization, or another
supported Abaqus study. Select it from the scientific question and evidence, not
from the reference fatigue case.

Not every detail needs a user answer. Experts should propose justified defaults
for low-risk choices. Never default a choice that changes the load path,
constitutive physics, safety factor, optimization objective, or scientific claim
without explicit approval.

The first complete Factorio package should contain:

1. a research dossier with question, hypothesis, scope, evidence, and decisions;
2. a simulation specification that another engineer can audit;
3. an Abaqus Python script with declared interpreter/version assumptions and no
   unresolved placeholders;
4. any scientifically required companion input such as a Tosca `.par` file;
5. a verification checklist covering model construction, mesh/convergence,
   boundary/load sanity, expected outputs, and comparison with evidence;
6. an independent review stating what is ready, what remains unverified, and what
   would be required before execution or publication.

Call an artifact generated, statically reviewed, or solver-verified according to
the evidence actually available. Without a real Abaqus/Relay execution result,
the strongest valid status is generated and reviewed, never executed or
validated.
