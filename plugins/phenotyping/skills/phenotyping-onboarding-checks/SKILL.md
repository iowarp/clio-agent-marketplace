---
name: phenotyping-onboarding-checks
title: Phenotyping Onboarding Checks
description: Use when first inspecting phenotyping data, to check its actual design, identities, methods, units, coverage and timing.
keywords:
- level:L1
- phenotyping
- miappe
- views
---

# Phenotyping onboarding checks

The files and the user's question are the starting point. Wide tables, nested
values, partial modalities, conflicting metadata and unfamiliar identifiers are
ordinary inputs. They do not need to fit a predetermined schema before useful
analysis.

Queries, code and derived outputs adapt to the export; repairing the export to
satisfy a validator changes the evidence. Derived files in the workspace leave the
export as delivered, by default under `<workspace_state>/datasets/<key>/` (see
`onboard-dataset`).

## The meaning the question depends on

- **Observation identity.** What a row represents, and how plants, pots, plots,
  scans, sessions and repeated measurements are identified, decides every join.
  A candidate join can leave rows unmatched or multiply them. An invented
  `unit_id` that only satisfies an example schema identifies nothing.
- **Design.** Factor labels, replication, blocks and position effects define it,
  and the actual group count includes missing or unequal cells. Digits in a
  treatment label do not establish a numeric dose.
- **Trait, method and scale.** MIAPPE's distinction is useful vocabulary: what
  was measured, how, and its unit or scale. These are concepts in the available
  evidence, not necessarily three named columns. Different methods are different
  measurements, and an unknown unit stays unknown.
- **Coverage and time.** Units, sensors and periods present, with partial rounds,
  gaps, repeats and uncertain time zones. A conversion of recorded times that
  requires a guess loses the recorded value.
- **Quality and uncertainty.** An empty issues table does not prove clean data. A
  suspicious value is a finding to investigate, not automatic permission to
  exclude or replace it.

Mappings, source references, limitations and transformations are part of the
result. Meaning that materially changes the answer is the data owner's to give,
and independent work does not wait on it. A comparison that cannot be identified
has a limit and still a supported descriptive result.

## Representation

Direct queries, a task-specific table, notebook or small script can all be
appropriate. Derived views earn their place through the requested analysis,
performance or reproducibility. Columns, keys, types and layout follow from the
observed data and the consumer's needs. Original values or source references
alongside material normalization keep it traceable.

The five schemas in `schemas/` are **optional examples**, not an export contract:

| Example | Possible use |
| --- | --- |
| `design` | One row per experimental unit when that unit is identifiable. |
| `observations` | Long measurements when trait, method and scale are established. |
| `spectra` | Wavelength measurements with known band identities and units. |
| `assets` | Actual images, masks or scans and their associated units. |
| `events` | Recorded imaging, treatment or watering events. |

An example helps only where it fits. Empty placeholder tables, spectra forced into
long form, or an analysis stopped because an example field is absent add nothing.
For a chosen example, this optional helper checks the output:

```text
uv run --no-project --with "pyarrow>=15" --with "jsonschema>=4.18" python "SKILL_ROOT/scripts/validate_views.py" DERIVED_TABLE --kind CHOSEN_EXAMPLE
```

For another representation, the invariants that matter are identities, join
cardinality, counts, units, missingness, selected values and the calculation.
Validator success establishes only the checks it actually performs.

Messy input is part of the analysis, not a request to fix the export.
