---
name: appl-core-exports
title: APPL-CORE Exports
description: Use when reading an APPL-CORE export - its format and supported export_version, its own self-description and files, and what each sensor measures.
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

- **The declared version** is in the manifest (and the README, if it states
  one); where it was read is part of the answer.
- **Version 6:** the rest of this skill applies.
- **Any other version, or none to be found:** this plugin's format knowledge
  may not hold. A card, views or derived tables built as if it were an
  APPL-CORE version 6 export would rest on an unchecked format, so the
  version mismatch is the headline for the person. The ways forward are the
  person's to choose: the format documentation for that version, the version
  confirmed with the data owners, or the files treated as unknown tabular data
  with `onboard-dataset` alone, labelled that way.

A new version can legitimately change this plugin; it is not something to adapt
around silently.

## Reading a version 6 export

- **Self-description.** The manifest, a README, column catalogs and
  per-modality documentation (often one document per modality, sometimes with
  YAML blocks) are starting points, not a mandatory reading order.
- **Declared against actual.** The manifest's paths, row counts, types and
  definitions can differ from what is present. Readable files are the ground
  truth when the manifest is incomplete or stale, and the discrepancy is a
  finding; editing the manifest is not part of analysis.
- **Sensors.** An export can carry any subset of the facility's modalities.
  Which are present, and each one's documentation (what it measures, its units
  and its processing), come from the export. `physiology-signals` and
  `size-and-growth-traits` hold the physics when a question depends on how a
  sensor works; the data owners know what the export's documentation does not
  say.
- **Missing or contradictory metadata** is a finding. Bounded samples of the
  tables test the documentation. Invented units, treatment meanings or join
  identities would make a parser or validator pass while making the analysis
  wrong.

`onboard-dataset` covers the inventory, audits and the experiment card, and
`phenotyping-onboarding-checks` design, identity, units and timing. Derived
files in the workspace leave the export as delivered. Bundled scripts and
schemas are examples to inspect, adapt or replace; they do not prescribe the
analysis.
