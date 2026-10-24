---
name: assess-data-quality
title: Assess Data Quality
description: Judge whether variables in HDF5, netCDF-4, ADIOS2 or Parquet files can be trusted and compared - what a variable states about itself, the checks to run with bounded reads, how to compare two variables, and which visual checks reveal problems.
keywords:
- level:L2
- data-quality
- comparison
- visual-checks
---

# Assess data quality

## What a variable states about itself

Collect this before judging values, and keep stated facts apart from checked
ones:

- name or path, dtype, shape and dimension names, and its coordinate
  variables (HDF5 dimension scales, netCDF coordinates, ADIOS2 steps);
- `units`, `long_name`, `standard_name`, `calendar`;
- missing-data conventions: `_FillValue`, `missing_value`, `valid_min`,
  `valid_max`, `valid_range`; packing: `scale_factor`, `add_offset`; flags:
  `flag_values`, `flag_masks`, `flag_meanings`;
- stored summaries: ADIOS2 per-block `Min`/`Max`, Parquet row-group statistics.
  They are hints: confirm them from the data before reporting them as results.

## Checks

Start with bounded reads (a slice, a step, a row group), then read fully when
the answer depends on it. Give every count with its denominator and the scope
you read.

- **Missing data**: NaN, nulls, fill and missing values, counted separately.
  A fill value that also occurs as a real measurement is a finding.
- **Range**: values outside the declared valid range or physically impossible
  for the stated quantity; extreme repeated values that look like sentinels.
- **Packing**: packed integers read as if they were physical values.
- **Shape of the values**: constant or near-constant arrays, all-zero blocks,
  quantization steps (low precision, float16, lossy compression).
- **Coordinates**: monotonic, unique, regularly spaced where they should be;
  gaps and repeated time stamps; time zones and calendars stated.
- **Coverage**: ADIOS2 blocks that leave holes in a global array; variables
  missing from some steps; HDF5 chunks never written (they read as the fill
  value).
- **Flags against data**: whether quality flags agree with the values they
  describe.

## Comparing variables

1. Establish that they measure the same thing: `standard_name` or
   documentation, units, and processing level.
2. Align them on shared coordinates before differencing: same grid, times and
   reference; interpolation or resampling is a stated analytical choice.
3. Convert units only between stated units; an unknown unit is a question.
4. State incompatibilities (units, resolution, time range, coordinate system)
   before any numbers.
5. Over the overlapping valid elements, report the count compared, mean and
   maximum absolute difference, RMS difference and correlation, and where the
   largest differences are.

## Visual checks

Choose the plot the data and the question support, from values you read:

| Data | Check |
|---|---|
| one variable's distribution | histogram (sentinels, quantization, outliers) |
| a series along time or another coordinate | line plot (gaps, steps, drift) |
| a 2-D field (one step or level) | heatmap of the slice (stripes, block edges, fill regions) |
| latitude and longitude | map |
| two paired variables | scatter with the 1:1 line |
| missing values in a grid | the missing-value mask as an image |

Say which slice, step or sample a plot shows. Load
`present-interactive-analysis` for an interactive view, or plot with a script
through `shell_bash` for a file.

## Reporting

Report what was stated, what you checked and what you infer, with the scope of
each check. Unknown units, flag meanings or fill conventions are questions for
the data owner, asked while independent checks continue. Write derived files
to the workspace so the source stays as delivered.
