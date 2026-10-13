---
name: appl-core-exports
title: APPL-CORE Exports
description: Discover an APPL-CORE export from actual files and self-description, reconcile metadata with observed tables, and adapt to missing documentation or unfamiliar versions without changing the source.
keywords:
- level:L2
- appl-core
- export-format
---

# APPL-CORE exports

The export is evidence to inspect, not a schema the agent may repair. Treat it
as read-only input. Keep generated code, notes and derived data outside the
bundle, even when a development copy happens to be writable.

Look for a manifest, README, column catalogs, modality documentation and actual
files. These are useful starting points, not a mandatory file list or reading
order. Compare declared paths, row counts, types and definitions with what is
present. Follow readable files when a manifest is incomplete or stale; report
that discrepancy instead of editing the manifest.

Record `export_version` when supplied. Version 6 is a documented example for
this pack, not the only version an agent may investigate. A missing or unfamiliar
version calls for inspecting structure and definitions, adapting the reader and
stating uncertainty. It is not by itself a reason to refuse the dataset. If a
particular binary format or operation cannot be read safely, identify that
limitation and continue with evidence that is accessible.

Machine-readable metadata may be absent, malformed or contradictory. Read the
surrounding documentation and compare it with bounded samples of actual tables.
Never invent units, treatment meanings or join identities to make a parser or
validator pass.

Use `onboard-dataset` for adaptable inspection and `phenotyping-onboarding-checks`
for scientific checks. Bundled scripts and schemas are examples to inspect,
choose, adapt or replace; they do not prescribe the analysis pipeline.
