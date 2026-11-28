---
name: convert-scientific-data
title: Convert Scientific Data
description: Use to convert HDF5 or netCDF-4 datasets or ADIOS2 variables to Parquet with an explicit dtype map and a verified result (bundles convert_to_parquet.py).
keywords:
- level:L2
- conversion
- hdf5
- adios2
- parquet
---

# Convert scientific data

A conversion is verified when the output's row count, missing values, dtypes
and per-column checksums match the source, and every lossy, transformed or
skipped field is reported with its reason. A file that merely exists is not a
conversion.

## What a conversion depends on

- **The source**, as its format skill (`hdf5`, `adios2`) and bounded reads
  show it: paths or variable names, dtypes, shapes, steps, attributes (units,
  `_FillValue`, `missing_value`, `scale_factor`, `add_offset`, `calendar`).
- **What a row is.** Parquet is a table. One-dimensional datasets of
  equal length, a compound (record) dataset, ADIOS2 global values per step, or
  one-dimensional global arrays per step fit. A gridded field (time x lat x
  lon) does not fit without a decision: flatten it with explicit coordinate
  columns, keep each row as a fixed-size list, or keep a gridded format
  (netCDF, Zarr). Which one is right depends on the consumer's needs, which the
  person usually knows.
- **The consumer** (pandas, Spark, DuckDB, an older reader): it decides the
  uint64, float16 and timestamp choices below.

## The dtype map

| Source | Parquet / Arrow | Default |
|---|---|---|
| bool, int8-64, uint8-32, float32/64 | same | copied |
| uint64 | uint64 (INT64 with an unsigned annotation) | copied; readers that ignore the annotation show values above 2^63-1 as negative |
| float16 | float32 | widened (exact); Parquet's own float16 type is too new for many readers |
| long double / float128 | none | skipped; float64 rounding loses precision |
| complex | struct of `real`, `imag` | refused unless requested (`--complex split`); a consumer may want that, magnitude/phase, or nothing |
| fixed-length or variable-length strings | string | decoded with the declared encoding (ASCII or UTF-8); bytes that do not decode stop the conversion |
| enum | dictionary of the declared labels | mapped; a value outside the mapping stops the conversion |
| compound | one column per member (top level), struct (nested) | mapped |
| fixed-size array member, extra dataset dimensions | fixed-size list | mapped; the element shape is recorded |
| variable-length sequences | list | mapped |
| object or region references | none | skipped: they point inside the HDF5 file |
| opaque, bitfield | none | skipped |
| scalar dataset | none | kept in the file's key-value metadata |
| CF time (`<unit> since <epoch>`) | timestamp[us, UTC] | kept numeric unless asked (`--cf-time decode`); only standard, gregorian and proleptic_gregorian calendars decode |
| `_FillValue` / `missing_value` | null | kept as values unless asked (`--mask-fill`); counts are reported either way |
| `scale_factor` / `add_offset` | float64 | kept packed unless asked (`--unpack`) |

Attributes travel with each column as field metadata (as JSON), and the
source path, its SHA-256, the options and every decision go into the file's
key-value metadata under `clio.conversion`.

## Skipped fields and meaning-changing choices

- **Skippable fields** have no meaning outside the source (references, opaque
  blobs) or were excluded by the person; the report lists them.
- **Meaning-changing choices** alter what the numbers mean or who can read them:
  complex representation, decoding time with a non-standard calendar, turning
  fill values into nulls, unpacking, rounding long doubles, uint64 for a reader
  that cannot take it, values compressed by a lossy ADIOS2 operator. They are the
  person's decisions; fields that do not depend on them convert regardless.
- **A failed check** stays failed: changing the comparison hides a real mismatch,
  and the mismatch is a finding.

## The bundled script

`load_skill` reports this skill's directory as `SKILL_ROOT`. The script carries
its dependencies (PEP 723); ADIOS2 input also needs `--with adios2`:

```text
uv run --no-project "SKILL_ROOT/scripts/convert_to_parquet.py" hdf5 SOURCE.h5 --group /GROUP -o OUT.parquet --report OUT.report.json
uv run --no-project "SKILL_ROOT/scripts/convert_to_parquet.py" hdf5 SOURCE.h5 --datasets /A /B -o OUT.parquet
uv run --no-project --with adios2 "SKILL_ROOT/scripts/convert_to_parquet.py" adios RUN.bp --variables VAR1 VAR2 [--steps FIRST:STOP] -o OUT.parquet
```

Options: `--complex split`, `--cf-time decode`, `--mask-fill`, `--unpack`,
`--skip NAME` (repeatable; a dataset, a column or `dataset.member`),
`--compression` (zstd by default), `--batch-rows`, `--overwrite`.

It writes in row batches, then reads the file back and checks:

- **rows**: expected, written and in the Parquet footer all agree;
- **schema**: the written schema is the planned one;
- **per column**: null count (zero, or the number masked), NaN count against
  the source (floating leaves inside lists and structs included), and a
  SHA-256 over the logical values. For copied, widened and decoded columns
  the expected checksum comes from the raw source values; for transformed
  columns (enum labels, structs, lists, masking, unpacking, time decoding) it
  comes from the converted values, and the report says so.

Exit status 0 means written and verified (skipped fields listed), 1 means a
check failed (the file is left for inspection; it is not a good output),
2 means nothing was written: a usage error, a field that cannot be converted
as asked, or the output already exists. The printed summary and the JSON
report (`--report`) list every column's action, checks and notes.

Limits: one output table per run; selected HDF5 datasets must share their
first-axis length; netCDF-4 coordinate variables are converted as ordinary
datasets, not joined; ADIOS2 local arrays and multi-dimensional variables are
refused (a custom script can select and reshape them); ADIOS2 arrays are read
twice (once to count rows). A workspace script that follows the same map and
checks, and reports the same way, is an equivalent conversion.

## Outputs

Outputs live in the workspace by default, not next to the source. A complete
conversion summary gives the source and output paths, rows, every column's
action and check, every skipped or lossy field with its reason, and the open
questions. `create_artifact` delivers it (`used` listing the source and the
Parquet file), with the JSON report beside the output.
