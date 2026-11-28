---
name: onboard-dataset
title: Onboard a Dataset
description: Use when inspecting unfamiliar data for the user's question, adapting checks to its actual files and keeping evidence, open questions and derived files in the workspace.
keywords:
- level:L0
- data-onboarding
- data-quality
- experiment-card
---

# Onboard a dataset

Onboarding means learning enough about the supplied data to answer the person's
question accurately, knowing the limits, and leaving useful evidence for later
work. A fixed loader, table schema, output format or full-dataset conversion is
not a prerequisite for useful analysis.

## The source as delivered

- Notes, code, cleaned copies, views and reports derived from the data live in
  the workspace by default, so the source stays as delivered. Fixing source
  files, editing a manifest or rewriting metadata is a separate data-editing task
  that the person asks for; exploration and analysis don't imply it. Outputs can
  go wherever the person wants them; CLIO's approval and sandbox settings decide
  what is permitted, and a denial is the answer to report.
- Queries, libraries and representations fit the observed structure best. Helper
  assumptions may not hold for a given dataset. Missing columns, nested values
  and inconsistent descriptions are findings to work with, not reasons to demand
  a cleaned export.
- CLIO supplies `CLIO_AGENT_WORKSPACE_STATE_DIR`; a useful default for per-dataset
  records is `<workspace_state>/datasets/<key>/`. Without it, the active
  workspace or a place the person names works. Source inspection does not need
  an experiment card.
- Observed values and analytical decisions are different things. Source
  references, mappings, exclusions and affected counts are what make decisions
  traceable. Derived representations do not change what the original data says.
- Scripts run with `shell_bash` (`uv run`), and `create_artifact` delivers files
  to the person, with its inputs listed in `used`.

## What the question depends on

- **Scope.** The source's actual files, access, formats and sizes, and its
  manifests, documentation and column catalogs, whose claims may differ from the
  data. The source declares a format and version. A loaded source skill that
  states a contract (a format and version range) defines what it supports,
  including its refusal of out-of-contract versions; without one, the structure
  itself is the guide.
- **Earlier evidence.** An existing card, notebook or report can help when its
  source identity, files, assumptions and results still match what the current
  answer depends on. A matching manifest does not establish unchanged data. A
  cached card can be stale, and rerunning every old conversion is rarely needed.
- **The data itself.** Schemas and bounded samples are cheap; full counts or
  distributions cost more and matter when the answer needs them. Keys, values,
  types, units, flags, missingness and coverage come from the data. Sample
  findings describe the sample. Expanding a wide table to match an example shape
  adds nothing.
- **Computational obstacles.** Column selection, joins, parsing, batching and
  output layout can all change with the evidence. A missing helper or an
  unsupported example schema means another justified approach. Material
  adaptations are part of the explanation.
- **Uncertain meaning.** Treatment definitions, units, time zones, ambiguous
  identifiers and competing interpretations are questions for the person when
  they affect the result. Unknown values stay unknown; independent work does not
  wait on them. A label does not establish a numeric dose or physical unit.
- **Computation and checks.** Direct queries or task-specific code both work.
  Join cardinality, retained and excluded counts, missingness, units and selected
  calculations checked against the source are the evidence. Only useful outputs
  need materializing. Reusable code is reproducible with its dependencies,
  invocation, decisions and relevant input fingerprints. Expensive work is worth
  repeating for verification, a change or the person's request, not as a ritual.
- **The result.** It consists of the inspected scope, supported answer, evidence,
  limits, questions and links to saved artifacts. An incomplete modality limits
  that claim; it does not invalidate unrelated evidence or require source repair.

## Optional helpers and records

`load_skill` reports this skill's directory as `SKILL_ROOT`. These are examples,
not a sequence. They read source inputs and write any reports to a separate
output location:

```text
uv run --no-project --with "pyarrow>=15" python "SKILL_ROOT/scripts/inventory.py" BUNDLE_ROOT --out OUTPUT_DIR/inventory.json
uv run --no-project --with "pyarrow>=15" --with "numpy>=1.24" python "SKILL_ROOT/scripts/audit_columns.py" TABLE --out OUTPUT_DIR/columns.json
uv run --no-project --with "pyarrow>=15" python "SKILL_ROOT/scripts/join_keys.py" TABLE_A TABLE_B --keys OBSERVED_KEYS --out OUTPUT_DIR/join.json
uv run --no-project --with "pyarrow>=15" python "SKILL_ROOT/scripts/flag_check.py" TABLE --flags OBSERVED_FLAG --signal OBSERVED_SIGNAL --out OUTPUT_DIR/flags.json
uv run --no-project python "SKILL_ROOT/scripts/card.py" status|init|record|verify BUNDLE_ROOT
```

`uv` runs them with the project's environment or the example's declared
dependencies. The optional card helper uses `CLIO_AGENT_WORKSPACE_STATE_DIR`, or
an explicit absolute `--store` for standalone use. Its manifest hash identifies a
record; its loader/view checks verify the files it records. They are not a
universal readiness test, scientific validation or a complete source fingerprint.
Legacy cards stay intact unless a separate migration is requested.

A Markdown card, notebook, task-specific script or another record can document
this work. `loader.py`, Parquet views, `prepared` status and a domain skill's
example schemas are optional choices; fabricated ones only satisfy a checklist.
Deliverables saved through `create_artifact` with their actual input references
remain available with provenance.

## Checks that can matter

- **Missingness and suspicious values.** Nulls, empty strings, nested values and
  possible sentinels such as extreme floats or repeated codes. Metadata and
  surrounding observations distinguish them. An uncertain encoding is a finding;
  nulling every unusual value loses information.
- **Duplicate or empty columns.** Content, types, coverage and definitions tell
  candidates apart. Similar names or nearby wavelengths may represent distinct
  measurements, so unresolved alternatives keep clear labels.
- **Flags and signal.** Quality flags mean something only against the
  measurements they describe. A universal flag, missing flag or empty issue table
  does not establish that the measurements should all be accepted or discarded.
- **Keys and joins.** Identity and cardinality come from the actual tables.
  Unmatched and multiplied rows show join problems. Evidence-backed mappings can
  be normalized; original identifiers and ambiguous cases remain.
- **Units and plausibility.** Scales, calibration, protocols and cross-sensor
  differences. Suspicious magnitudes call for investigation, not an invented
  conversion. Some comparisons are supported and others are not.
- **Timing and design.** Repeated observations, gaps, partial rounds, group sizes
  and confounding. Aggregation and models depend on the actual design; repeated
  measurements of one unit are not independent units.

The card helper offers example finding topics such as `sentinel-values`,
`key-format-mismatch`, `declared-vs-actual` and `unit-scale-suspect`. Findings
outside that vocabulary are still findings; the example taxonomy is not complete.

Dataset-specific facts and decisions belong in workspace records. General lessons
can be proposed separately. Analysing data does not authorize changing installed
shared skills or the original dataset.