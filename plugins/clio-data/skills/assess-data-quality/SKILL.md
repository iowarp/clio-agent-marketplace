---
name: assess-data-quality
title: Assess Data Quality
description: Use to judge whether variables in HDF5, netCDF-4, ADIOS2 or Parquet files can be trusted and compared, with bounded-read and visual checks.
keywords:
- level:L2
- data-quality
- comparison
- visual-checks
---

# Assess data quality

## What a variable states about itself

These are stated facts, distinct from checked ones, and values mean little
without them:

- name or path, dtype, shape and dimension names, and its coordinate
  variables (HDF5 dimension scales, netCDF coordinates, ADIOS2 steps);
- `units`, `long_name`, `standard_name`, `calendar`;
- missing-data conventions: `_FillValue`, `missing_value`, `valid_min`,
  `valid_max`, `valid_range`; packing: `scale_factor`, `add_offset`; flags:
  `flag_values`, `flag_masks`, `flag_meanings`;
- stored summaries: ADIOS2 per-block `Min`/`Max`, Parquet row-group statistics.
  They are hints until the data confirms them.

## Checks

Bounded reads (a slice, a step, a row group) are cheap; a full read matters
when the answer depends on it. A count means something with its denominator and
the scope read.

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

- Two variables are comparable when they measure the same thing: `standard_name`
  or documentation, units, and processing level.
- Differences are meaningful only on shared coordinates: same grid, times and
  reference; interpolation or resampling is an analytical choice.
- Unit conversion works only between stated units; an unknown unit is a question.
- Incompatibilities (units, resolution, time range, coordinate system) qualify
  every number that follows.
- Over the overlapping valid elements, the usual summary is the count compared,
  mean and maximum absolute difference, RMS difference and correlation, and where
  the largest differences are.

## Visual checks

Plots that suit each kind of data, drawn from values actually read:

| Data | Check |
|---|---|
| one variable's distribution | histogram (sentinels, quantization, outliers) |
| a series along time or another coordinate | line plot (gaps, steps, drift) |
| a 2-D field (one step or level) | heatmap of the slice (stripes, block edges, fill regions) |
| latitude and longitude | map |
| two paired variables | scatter with the 1:1 line |
| missing values in a grid | the missing-value mask as an image |

A plot is readable only with the slice, step or sample it shows.
`present-interactive-analysis` gives an interactive view; a script through
`shell_bash` produces a file.

## Reporting

What was stated, what was checked and what is inferred are different kinds of
result, each with the scope of its check. Unknown units, flag meanings or fill
conventions are questions for the data owner; independent checks do not depend
on them. Derived files live in the workspace so the source stays as delivered.
