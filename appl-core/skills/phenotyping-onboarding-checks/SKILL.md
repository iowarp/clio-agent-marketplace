---
name: phenotyping-onboarding-checks
title: Phenotyping Onboarding Checks
description: Inspect actual design, identities, methods, units, coverage and timing in phenotyping data. Adapt checks and derived representations to the supplied files and question; bundled schemas are optional examples.
keywords:
- level:L1
- phenotyping
- miappe
- views
---

# Phenotyping onboarding checks

Start from the files and the user's question. Wide tables, nested values,
partial modalities, conflicting metadata and unfamiliar identifiers are ordinary
inputs. They do not need to fit a predetermined schema before useful analysis.

Treat the source export as read-only input, even when its mount allows writes.
Adapt queries, code and derived outputs; do not repair the export to satisfy a
validator. Keep outputs outside it, usually under
`<workspace_state>/datasets/<key>/` or another permitted workspace location.

## Establish the meaning needed for the question

- **Observation identity.** Determine what a row represents and how plants, pots,
  plots, scans, sessions and repeated measurements are identified. Test candidate
  joins and report unmatched or multiplied rows. Do not invent `unit_id` just to
  satisfy an example schema.
- **Design.** Inspect factor labels, replication, blocks and position effects.
  Count actual groups, including missing or unequal cells. Digits in a treatment
  label do not establish a numeric dose.
- **Trait, method and scale.** MIAPPE's distinction is useful vocabulary: what
  was measured, how, and its unit or scale. Map those concepts to the available
  evidence; they need not be three named columns. Keep different methods
  distinguishable and leave unknown units unknown.
- **Coverage and time.** Establish which units, sensors and periods are present.
  Account for partial rounds, gaps, repeats and uncertain time zones. Preserve
  recorded times when converting them would require a guess.
- **Quality and uncertainty.** Check the values and flags relevant to the answer.
  An empty issues table does not prove clean data. A suspicious value is a finding
  to investigate, not automatic permission to exclude or replace it.

Record mappings, source references, limitations and transformations. Ask about
meaning that materially changes the answer while continuing independent work.
When a comparison cannot be identified, explain the limit and provide the
supported descriptive result.

## Choose a useful representation

Direct queries, a task-specific table, notebook or small script can all be
appropriate. Materialize derived views when they help the requested analysis,
performance or reproducibility. Select columns, keys, types and layout from the
observed data and the consumer's needs. Preserve original values or source
references alongside material normalization.

The five schemas in `schemas/` are **optional examples**, not an export contract:

| Example | Possible use |
| --- | --- |
| `design` | One row per experimental unit when that unit is identifiable. |
| `observations` | Long measurements when trait, method and scale are established. |
| `spectra` | Wavelength measurements with known band identities and units. |
| `assets` | Actual images, masks or scans and their associated units. |
| `events` | Recorded imaging, treatment or watering events. |

Use only examples that fit. Do not create empty placeholder tables, force all
spectra into long form, or stop a valid analysis because an example field is
absent. When deliberately choosing an example, this optional helper checks that
chosen output:

```text
uv run --no-project --with "pyarrow>=15" --with "jsonschema>=4.18" python "SKILL_ROOT/scripts/validate_views.py" DERIVED_TABLE --kind CHOSEN_EXAMPLE
```

For another representation, check the invariants that matter: identities, join
cardinality, counts, units, missingness, selected values and the calculation.
Validator success establishes only the checks it actually performs.

## Report

Explain what the available design and measurements support, what is uncertain,
which evidence was inspected and where any outputs were saved. Messy input is
part of the analysis, not a request to fix the export.
