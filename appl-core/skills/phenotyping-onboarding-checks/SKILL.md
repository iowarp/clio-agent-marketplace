---
name: phenotyping-onboarding-checks
title: Phenotyping Onboarding Checks
description: DRAFT. Turn any plant-phenotyping export into the five validated view shapes (design, observations, spectra, assets, events) using MIAPPE trait/method/scale vocabulary, check design balance and factor encoding, and list what is missing. Use after onboard-dataset on phenotyping data.
keywords:
- level:L1
- phenotyping
- miappe
- views
---

# Phenotyping onboarding checks (draft)

The seam between facility-specific exports and phenotyping analysis is a set
of five table shapes. The loader written during `onboard-dataset` produces
them; analyses read only them. Each shape has a JSON Schema in `schemas/`
(one row per object) and `scripts/validate_views.py` checks whole tables:

```text
uv run --no-project --with "pyarrow>=15" --with "jsonschema>=4.18" python "SKILL_ROOT/scripts/validate_views.py" DATASET_DIR/views/*.parquet
```

`DATASET_DIR` is the dataset's directory in the active workspace,
`<workspace_root>/.clio/datasets/<key>/`, as printed by
`card.py status BUNDLE_ROOT --store WORKSPACE_ROOT` (`dataset_dir:`). Views
live there, never under the export's bundle root, which is read-only input.

Views are named by shape prefix (`design...`, `observations...`, `spectra...`,
`assets...`, `events...`) so the validator infers the schema; use `--kind`
otherwise. Validation must pass before any view is recorded in the card.

## The five shapes

| Shape | One row = | Key | Notes |
| --- | --- | --- | --- |
| `design` | observation unit (plant/pot/plot) | `unit_id` | factors: genotype, treatment (always a string label), optional `treatment_value` + `treatment_unit` only when the owners confirm a dose, replicate, block, position |
| `observations` | unit x time x variable | `unit_id, time, trait, method, scale` | long format; `value` null when missing, never a code |
| `spectra` | unit x time x sensor x wavelength | `unit_id, time, sensor, wavelength_nm` | wavelength parsed from metadata or column names, in nm |
| `assets` | unit x time x file | `unit_id, time, kind, path` | paths relative to bundle root; `shared_frame` + crop when one file shows several units |
| `events` | imaging round / treatment / watering | `event_id` | status as recorded (completed, aborted, warning ...) |

MIAPPE vocabulary for `observations`: an observed **variable** is
**trait** (what: "projected leaf area") + **method** (how: sensor, algorithm,
mask or source choice) + **scale** (unit: `px`, `mm2`, `ratio`, `a.u.`). Two
values of the same trait from different methods are different variables; never
merge them into one column.

## Checks

- **Design balance.** Count units per factor combination from `design`.
  Report the table of counts, empty cells, and unequal replication. An
  unbalanced design changes which tests are valid (`treatment-response`).
- **Factor encoding.** Is the treatment a numeric dose (ordered, with a unit)
  or a category (control vs treated, named compounds)? Look at the values,
  the docs, and any label that encodes the design. If the export does not say
  what the treatment is or its unit, ask the data owners; keep `treatment` as
  a string and leave `treatment_value` null until they answer.
- **Duplicated factors.** The same factor stored in several columns, or also
  inside a composite label: check they agree row by row; keep one.
- **Coverage.** Which units are present in `design` but absent from a sensor's
  observations, and at which times; report per sensor.
- **Time.** Units observed several times per period; sessions that are split,
  aborted, or partial; the time zone assumption. Record in `events`.
- **Variables.** For every trait, record method and scale; flag traits whose
  scale is unknown or suspicious (see `size-and-growth-traits`,
  `physiology-signals`).
- **What is missing.** List what an analysis would need but the export does
  not provide (units, treatment meaning, calibration, masks, raw data), and
  put each item under the card's open questions.

## Output to the user

A design table (counts per cell), a coverage table (units x sensor x
sessions), the validator result per view, and the missing-information list.
Use generic tables and charts (presets first) when a view helps.
