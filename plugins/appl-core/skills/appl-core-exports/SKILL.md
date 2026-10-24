---
name: appl-core-exports
title: APPL-CORE Exports
description: The APPL-CORE export contract (format, supported export_version, refusal of other versions) and how to read an export from its own self-description and actual files, reconciling metadata with observed tables and finding what each sensor measures in the export's documentation.
keywords:
- level:L2
- appl-core
- export-format
---

# APPL-CORE exports

## The contract

This plugin covers **APPL-CORE exports with `export_version` 6**: the bundle the
APPL-CORE pipeline of ORNL's automated plant-phenotyping facility (OPAL) writes,
with a machine-readable manifest that declares `export_version`, per-modality
tables, asset directories and documentation. "Any export" means any experiment
exported in that version: other species, treatments, designs, sensor sets and
sizes. Version 6 is the only version this plugin has been tested on.

1. **Read the declared version first**, from the manifest (and the README, if it
   states one). Report what you read and where.
2. **Version 6:** proceed with the rest of this skill.
3. **Any other version, or none you can find:** stop the APPL-CORE analysis and
   say so plainly in the first sentence of your answer: the export declares
   version N (or no version), this agent supports version 6, and its format
   knowledge may not hold. Do not write a card, views or derived tables for it as
   an APPL-CORE export. Offer the user the choices: send the format
   documentation for that version, confirm the version with the data owners, or
   treat the files as unknown tabular data with `onboard-dataset` alone, labelled
   that way. Proceed only with the one they choose.

A new version can legitimately change this plugin; it is not something to adapt
around silently.

## Reading a version 6 export

- **Self-description first.** Look for the manifest, a README, column catalogs
  and per-modality documentation (often one document per modality, sometimes
  with YAML blocks). These are starting points, not a mandatory reading order.
- **Declared against actual.** Compare the manifest's paths, row counts, types
  and definitions with what is present. Follow readable files when the manifest
  is incomplete or stale, and report the discrepancy; editing the manifest is
  not part of analysis.
- **Sensors.** An export can carry any subset of the facility's modalities.
  Discover which are present and read each one's documentation for what it
  measures, its units and its processing. When a question depends on how a
  sensor works, use the physics in `physiology-signals` and
  `size-and-growth-traits`; when the export's documentation does not say
  something the analysis needs, ask the data owners.
- **Missing or contradictory metadata** is a finding. Compare the documentation
  with bounded samples of the tables. Never invent units, treatment meanings or
  join identities to make a parser or validator pass.

Use `onboard-dataset` for the inventory, audits and the experiment card, and
`phenotyping-onboarding-checks` for design, identity, units and timing. Write
derived files to the workspace so the export stays as delivered. Bundled
scripts and schemas are examples to inspect, adapt or replace; they do not
prescribe the analysis.
