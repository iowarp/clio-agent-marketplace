---
name: onboard-dataset
title: Onboard a Dataset
description: Inspect unfamiliar data for the user's question, adapt checks and code to its actual files and environment, and preserve evidence and unresolved meaning, writing derived files to the workspace so the source stays as delivered. Scripts and cards are optional aids.
keywords:
- level:L0
- data-onboarding
- data-quality
- experiment-card
---

# Onboard a dataset

Learn enough about the supplied data to answer the user's question accurately,
explain the limits, and leave useful evidence for later work. Adapt the analysis
to the files and environment. A fixed loader, table schema, output format or
full-dataset conversion is not a prerequisite for useful analysis.

## Keep the source as delivered and adapt the analysis

- By default, write everything you derive to the workspace so the source stays
  as delivered: notes, code, cleaned copies, views and reports. Fixing source
  files, editing a manifest or rewriting metadata is a separate data-editing task
  that the user asks for; exploration and analysis don't imply it. If the user
  wants outputs somewhere else, follow them; CLIO's approval and sandbox settings
  decide what is permitted, and a denial is reported, not pre-empted.
- Select queries, libraries and representations from the observed structure.
  Inspect helper assumptions; adapt or replace a helper that does not fit.
  Missing columns, nested values and inconsistent descriptions are findings to
  work with, not reasons to demand a cleaned export.
- CLIO supplies `CLIO_AGENT_WORKSPACE_STATE_DIR`; a useful default for per-dataset
  records is `<workspace_state>/datasets/<key>/`. If it is unavailable, use the
  active workspace or ask where outputs should go. Source inspection can continue
  without creating an experiment card.
- Preserve the distinction between observed values and analytical decisions.
  Record source references, mappings, exclusions and affected counts. Derived
  representations do not change what the original data says.
- Write scripts and run them with `shell_bash` (`uv run`), and deliver anything
  the user should receive with `create_artifact`, listing its inputs in `used`.

## Work from the question

1. **Establish the scope.** Locate the source and inspect actual files, access,
   formats and sizes. Read relevant manifests, documentation and column catalogs
   when available, and compare their claims with the data. Report the format
   and version the source declares. When a loaded source skill states a contract
   (a format and version range), follow it, including its refusal of
   out-of-contract versions; without one, investigate the structure.
2. **Reuse evidence critically.** An existing card, notebook or report can help.
   Check the source identity and the files, assumptions and results the current
   answer depends on. A matching manifest does not establish unchanged data.
   Reinspect changed or uncertain parts; do not blindly trust a cached card or
   rerun every old conversion by default.
3. **Inspect relevant data.** Start with schemas and bounded samples, then check
   full counts or distributions when the answer needs them. Discover actual keys,
   values, types, units, flags, missingness and coverage. Limit sample findings to
   the sample. Do not expand a wide table just to match an example shape.
4. **Resolve computational obstacles.** Adjust column selection, joins, parsing,
   batching and output layout using observed evidence. A missing helper or an
   unsupported example schema calls for another justified approach. Leave the
   source as delivered and explain material adaptations.
5. **Handle uncertain meaning.** Ask about treatment definitions, units, time
   zones, ambiguous identifiers or competing interpretations when they affect
   the result. Keep unknown values unknown and continue independent work. Do not
   force a numeric dose or physical unit from a label.
6. **Compute and check.** Use direct queries or task-specific code as appropriate.
   Check join cardinality, retained and excluded counts, missingness, units and
   selected calculations against the source. Materialize only useful outputs.
   When reusable code is valuable, record dependencies, invocation, decisions
   and relevant input fingerprints. Repeat expensive work when verification,
   a change or the user requires it, not as an unconditional ritual.
7. **Explain the result.** State the inspected scope, supported answer, evidence,
   limits and questions. Link saved artifacts. An incomplete modality limits
   that claim; it does not invalidate unrelated evidence or require source repair.

## Optional helpers and records

`load_skill` reports this skill's directory as `SKILL_ROOT`. These are examples,
not a mandatory sequence. They read source inputs and write any reports to a
separate output location:

```text
uv run --no-project --with "pyarrow>=15" python "SKILL_ROOT/scripts/inventory.py" BUNDLE_ROOT --out OUTPUT_DIR/inventory.json
uv run --no-project --with "pyarrow>=15" --with "numpy>=1.24" python "SKILL_ROOT/scripts/audit_columns.py" TABLE --out OUTPUT_DIR/columns.json
uv run --no-project --with "pyarrow>=15" python "SKILL_ROOT/scripts/join_keys.py" TABLE_A TABLE_B --keys OBSERVED_KEYS --out OUTPUT_DIR/join.json
uv run --no-project --with "pyarrow>=15" python "SKILL_ROOT/scripts/flag_check.py" TABLE --flags OBSERVED_FLAG --signal OBSERVED_SIGNAL --out OUTPUT_DIR/flags.json
uv run --no-project python "SKILL_ROOT/scripts/card.py" status|init|record|verify BUNDLE_ROOT
```

Use `uv` with the project's environment or the example's declared dependencies.
The optional card helper uses `CLIO_AGENT_WORKSPACE_STATE_DIR`, or an explicit
absolute `--store` for standalone use. Its manifest hash identifies a record;
its loader/view checks verify the files it records. They are not a universal
readiness test, scientific validation or a complete source fingerprint.
Keep legacy cards intact unless a separate migration is requested.

A Markdown card, notebook, task-specific script or another record can document
this work. `loader.py`, Parquet views, `prepared` status and a domain skill's
example schemas are optional choices. Do not fabricate them to satisfy a
checklist. Save user deliverables through `create_artifact` with their actual
input references so the result remains available with provenance.

## Checks to select when relevant

- **Missingness and suspicious values.** Inspect nulls, empty strings, nested
  values and possible sentinels such as extreme floats or repeated codes. Compare
  metadata and surrounding observations before interpreting them. Flag uncertain
  encodings; do not automatically null every unusual value.
- **Duplicate or empty columns.** Compare content, types, coverage and definitions
  before selecting a candidate. Similar names or nearby wavelengths may represent
  distinct measurements. Retain unresolved alternatives with clear labels.
- **Flags and signal.** Check quality flags against the measurements they describe.
  A universal flag, missing flag or empty issue table does not establish that the
  measurements should all be accepted or discarded.
- **Keys and joins.** Establish identity and cardinality from the actual tables.
  Count unmatched and multiplied rows. Normalize only evidence-backed mappings,
  preserving original identifiers and ambiguous cases.
- **Units and plausibility.** Inspect scales, calibration, protocols and
  cross-sensor differences. Suspicious magnitudes call for investigation, not an
  invented conversion. State which comparisons are supported.
- **Timing and design.** Inspect repeated observations, gaps, partial rounds,
  group sizes and confounding. Choose aggregation and models for the actual
  design; do not silently treat repeated measurements of one unit as independent units.

The card helper offers example finding topics such as `sentinel-values`,
`key-format-mismatch`, `declared-vs-actual` and `unit-scale-suspect`. Use them when
helpful, and describe findings outside that vocabulary as well. Do not discard a
new finding because an example taxonomy omitted it.

Keep dataset-specific facts and decisions in workspace records. General lessons
may be proposed separately. Analysing data does not authorize changing installed
shared skills or the original dataset.
