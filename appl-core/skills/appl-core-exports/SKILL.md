---
name: appl-core-exports
title: APPL-CORE Exports
description: PLACEHOLDER. How to start reading an APPL-CORE plant-phenotyping export - from its self-description (manifest.json, per-modality column catalogs, README, and docs/modalities YAML blocks) - and the export_version check. Load before onboarding an APPL-CORE export.
keywords:
- level:L2
- appl-core
- export-format
---

# APPL-CORE exports (placeholder)

Status: minimal on purpose. Pitfall checks are added here only after they are
seen in two or more APPL-CORE exports (or stated in the format docs); until
then they live in each experiment's card.

## Version check (do this first)

Read `export_version` from the export's `manifest.json`. This pack supports
**export_version 6**. For any other value -- or when it is missing -- stop:
do not write a loader or views; tell the user the version found, that this
agent was built for version 6, and what would be needed (a check of the
changed format against the version 6 contract). Do not "try anyway".

## The export describes itself

Start from the export's own files, in this order, then follow
`onboard-dataset`:

1. `manifest.json`: identity, `export_version`, `generated_at`, per-modality
   file lists and row counts, asset directories, and the documentation index.
   Discover tables from it instead of listing directories.
2. The per-modality `-columns` catalogs: which columns each table has and
   their role.
3. `README.md` at the export root.
4. `docs/modalities/*.md`: one document per modality, with machine-readable
   YAML blocks (identifiers, status, outputs, definitions). Parse the YAML
   blocks rather than paraphrasing the prose.

Record what these files state as `[stated]` facts in the card, with the file
as the source, and check the ones your analysis depends on.
