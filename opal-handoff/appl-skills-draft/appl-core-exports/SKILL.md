---
name: appl-core-exports
title: Read an APPL-CORE export
description: How to open, navigate and join any APPL-CORE plant-phenotyping export from its own manifest and docs, and which format-level problems to check for. Load before onboarding or querying an APPL-CORE export.
keywords:
- level:L2
- appl-core
- export
- manifest
---

# Read an APPL-CORE export

> DRAFT (handoff). Pitfall checks marked **[candidate]** were seen in only one export so far.
> Keep them as checks; promote them (drop the marker) only after a second export shows the
> same thing, or the format docs state it. Never add counts, IDs, dates or magnitudes.

APPL-CORE exports **describe themselves**. Read what they say about themselves first, and let
them tell you what exists. Never assume a sensor, table or column is present.

## Contract
- **The export is recognised by `manifest.json`** at the root, with `export_version`. This skill
  covers **version 6**. For any other version, **stop and report** that the format is
  unsupported. Don't guess.
- **Everything is indexed by the manifest:**
  - `modalities[].files` (logical name → Parquet path);
  - `asset_dirs`;
  - per-table row counts;
  - `documentation[]`;
  - `appl_vision`.
- **Build paths from the manifest, never by hand.**

## First reads, in order
1. **`README.md`:** the human overview. It lists sensors with rows, sensors that were requested but have no rows, and the side tables.
2. **`manifest.json`:** the machine index.
3. **`docs/experiment-export-summary.md`** and **`docs/modalities/<SENSOR>.md`:** each has a YAML block (`modality_id`, `pipeline_status`, `feature_outputs`, units, formulas) plus prose. These docs are the authority on what a trait means and on known gaps. Quote them as *stated*.
4. **`<sensor>/<sensor>-columns.csv`:** the column dictionary (`table, column, role`). Roles include `identity`, `timestamp`, `trait`, `design`, `metadata`, `asset`, `signature`, `image_geometry`, `feature_geometry`, `thumbnail_*`. The `trait` role can also contain non-measurements (QC flags, format strings). Filter them.
5. **`data-issues`:** the export's own issue list. An empty list does **not** mean the data is clean.

## Table model
- **Per sensor:**
  - `-features` (measurements + geometry + QC + asset paths);
  - `-metadata` (capture context);
  - `-design` (factors repeated on each row).

  All three have the same rows in the same order, keyed by `sample_key`.
- **Some sensors add long tables** (the manifest lists them): values/variables/samples/parameter-images tables for fluorescence, values/leaf-values/variables for 3D, and `signatures` (one column per wavelength) for hyperspectral.
- **Top-level side tables:** plant weights, heights when present, and experiment metadata.
- **Assets:** thumbnails (usually one image per tray/frame), per-plant masks in frame coordinates, and geometry text files. Paths are relative to the export root. Crop a plant using the features table's ROI columns.
- **CSV and Parquet hold the same rows.** Use Parquet: it keeps types and is much smaller.

## Joining
- **Within a sensor:** join on `sample_key`.
- **Across sensors:** join on (`experiment_id`, `plant_id`, `round_id`), with an **outer join**. Sensors have very different coverage and cadence.
- **Check key formats before joining.** Long tables can use a different `sample_key` shape (case, suffixes), or none at all, so join those on the identity columns.
- **Imaging rounds are the unit of repetition.** Several rounds can fall on one day, and sensors run on different schedules. Decide how to aggregate (per round, per day, per slot) before comparing sensors.

## Checks for this format
Run the general audit (the `onboard-dataset` scripts), then specifically:
- **[candidate]** Long value tables may encode "no value" as the largest float instead of null. Check `value` columns for sentinel extremes before aggregating.
- **[candidate]** One variable can appear under two provenance kinds (the vendor scalar vs a masked median from a parameter image). Pick one and say which.
- **[candidate]** Variable names in long tables may carry literal quote characters. Normalise them before matching.
- **[candidate]** Signature tables may contain a second, empty, text-typed copy of each band column, labelled with a slightly different wavelength. Keep only numeric band columns.
- **[candidate]** Rows with no measurement may not carry an "empty" QC flag. Filter on coverage or trait presence, not on flags. Some flags appear on nearly every row and carry no information.
- **[candidate]** List-like columns (flags, ID lists) may be text-encoded in CSV.
- **[candidate]** Treatment levels may be stored as text. Convert them before ordering doses.
- **Treatment meaning and units are usually absent from the export.** Ask the data owner and record the answer in the experiment card.

## What goes where
- **Facts about this export** (which sensors, counts, dates, the traps found) → the experiment card, **not this skill**.
- **A new check** that shows up again on a second export → propose adding it here as a check.
