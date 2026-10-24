---
name: convert-scientific-data
title: Convert Scientific Data
description: Convert HDF5 (including netCDF-4) datasets or ADIOS2 BP4/BP5 variables to Parquet with an explicit dtype map, decide when a field is skipped and when to ask, and prove the result with row, null, NaN, dtype and per-column checksum checks. Bundles convert_to_parquet.py, which writes, reads back and verifies.
keywords:
- level:L2
- conversion
- hdf5
- adios2
- parquet
---

# Convert scientific data

A conversion is done only when the output's row count, missing values, dtypes
and per-column checksums match the source, and every lossy, transformed or
skipped field is reported with its reason. A file that merely exists is not a
conversion.

## Before converting

1. **Inspect the source** with its format skill (`hdf5`, `adios2`) and bounded
   reads: paths or variable names, dtypes, shapes, steps, attributes (units,
   `_FillValue`, `missing_value`, `scale_factor`, `add_offset`, `calendar`).
2. **Decide what a row is.** Parquet is a table. One-dimensional datasets of
   equal length, a compound (record) dataset, ADIOS2 global values per step, or
   one-dimensional global arrays per step fit. A gridded field (time x lat x
   lon) does not fit without a decision: flatten it with explicit coordinate
   columns, keep each row as a fixed-size list, or keep a gridded format
   (netCDF, Zarr). Ask the user when the consumer's needs are not stated.
3. **Name the consumer** when you know it (pandas, Spark, DuckDB, an older
   reader): it decides the uint64, float16 and timestamp choices below.

## The dtype map

| Source | Parquet / Arrow | Default |
|---|---|---|
| bool, int8-64, uint8-32, float32/64 | same | copied |
| uint64 | uint64 (INT64 with an unsigned annotation) | copied; report it: readers that ignore the annotation show values above 2^63-1 as negative |
| float16 | float32 | widened (exact); Parquet's own float16 type is too new for many readers |
| long double / float128 | none | skipped; ask whether float64 rounding is acceptable |
| complex | struct of `real`, `imag` | refused unless asked (`--complex split`); ask whether the consumer wants that, magnitude/phase, or nothing |
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

## Skip, or ask

- **Skip and report** a field that has no meaning outside the source
  (references, opaque blobs) or that the user excluded.
- **Ask** when the choice changes what the numbers mean or who can read them:
  complex representation, decoding time with a non-standard calendar, turning
  fill values into nulls, unpacking, rounding long doubles, uint64 for a reader
  that cannot take it, values compressed by a lossy ADIOS2 operator. Continue
  with the fields that do not depend on the answer.
- **Never** fix a failed check by changing the comparison. A mismatch is a
  finding to report.

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
check failed (the file is left for inspection; do not deliver it as good),
2 means nothing was written: a usage error, a field that cannot be converted
as asked, or the output already exists. The printed summary and the JSON
report (`--report`) list every column's action, checks and notes.

Limits: one output table per run; selected HDF5 datasets must share their
first-axis length; netCDF-4 coordinate variables are converted as ordinary
datasets, not joined; ADIOS2 local arrays and multi-dimensional variables are
refused (select and reshape them in your own script); ADIOS2 arrays are read
twice (once to count rows). When the script does not fit, write your own in
the workspace that follows the same map and checks, and report the same way.

## Deliver

Write outputs to the workspace, never next to the source unless the user
asks. Report the source and output paths, rows, every column's action and
check, every skipped or lossy field with its reason, and the open questions.
Deliver that summary with `create_artifact` (`used` listing the source and
the Parquet file), keeping the JSON report beside the output.
