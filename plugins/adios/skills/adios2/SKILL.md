---
name: adios2
title: ADIOS2 BP files
description: Use for ADIOS2 output (.bp directories from the BP4 or BP5 engine) - layout, steps, selections, blocks, attributes, the adios2 Python APIs, bpls, engines and compression.
keywords:
- level:L2
- adios2
- format
---

# ADIOS2 BP files

## Contract

This skill covers files written by the **BP4 and BP5** engines of ADIOS2. BP3
output (a single `.bp` file, often with a `.bp.dir` folder) and the streaming
engines (SST, SSC, DataMan) are outside it: their layout differs, and this
skill does not describe it.

## Layout

A BP4 or BP5 "file" is a directory, `name.bp/`:

| File | Engine | Holds |
|---|---|---|
| `data.0`, `data.1`, ... | both | the data, one subfile per writing aggregator |
| `md.0`, `md.idx` | both | metadata and its step index |
| `mmd.0` | BP5 | the metadata-metadata BP5 adds |
| `profiling.json` | both, optional | writer timing |

`mmd.0` tells BP5 from BP4. The directory is the unit; a copy of only some of
these files is not a readable BP file.

## The data model

- **Steps** are the output cycles (often time steps). `AvailableStepsCount`
  says in how many steps a variable was written; a variable can be missing
  from some steps, and its shape can change between steps, so a regular series
  is not guaranteed.
- **Variables** have a name (often path-like, `group/field`), a type and a
  `Shape`:
  - **global array**: `Shape` is the global dimensions; writers each wrote
    **blocks** with their own `Start` and `Count`. Readers select with
    `start` and `count` in global coordinates.
  - **global value**: empty `Shape` and `SingleValue` true; one value per step.
  - **local array**: empty `Shape` and `SingleValue` false; each writer's block
    stands alone and is read by `block_id`.
  - **local value**: one value per writer; readers see a one-dimensional
    array with one element per writer.
- **Blocks** keep their own `Min`/`Max` and the `WriterID`;
  `all_blocks_info(name)` lists them per step. Gaps or overlaps between blocks
  are possible, so a global array is not necessarily dense.
- **Attributes** are global or belong to a variable (`var/attr`, separator
  `/`). They usually hold units, descriptions and run parameters, without which
  values are hard to interpret.
- Dimension order is as written (row-major from C/C++/Python writers). The
  block metadata's `IsReverseDims` marks blocks recorded in reversed
  (column-major) order, as Fortran writers produce; whether to transpose
  depends on it.

## Reading with Python

The high-level API changed between releases; `adios2.__version__` says which
is installed.

**2.10 and later** (`adios2.FileReader` for random access, `adios2.Stream`
for step-by-step):

```python
import adios2
with adios2.FileReader(path) as f:
    f.available_variables()            # name -> {Type, Shape, AvailableStepsCount, SingleValue, Min, Max}
    f.available_attributes()           # "var/attr" or "attr" -> {Type, Elements, Value}
    f.num_steps()
    f.read(name, start=[0, 0], count=[10, 10])                        # first step
    f.read(name, start=[0, 0], count=[10, 10], step_selection=[2, 3])  # steps 2..4
    f.read(local_name, block_id=0)
with adios2.Stream(path, "r") as s:
    for _ in s.steps():
        s.current_step(); s.available_variables(); s.read(name, start, count)
```

Without `step_selection`, `FileReader.read` returns the first step. With
`step_selection=[first, n]`, the steps are stacked along the first axis (two
steps of a `(rows, cols)` selection come back as `(2*rows, cols)`), not as a
new axis; a reshape recovers the step axis. `Stream.minmax(name)` exists from 2.12.

**2.9** has no `FileReader` or `Stream` in Python; it has `adios2.open(path, "r")`
and `for fstep in fh: fstep.read(name, start, count)`, or random access with
`fh.read(name, start, count, step_start, step_count)`.

Bounded selections are safe before the sizes are known; a whole variable can be
large. Reads run as scripts through `shell_bash`, for example
`uv run --no-project --with adios2 --with numpy python script.py`.

**The PyPI wheel** (`pip install adios2`) is built without MPI and without the
compression operators (Blosc, BZip2, ZFP, SZ, MGARD, PNG). A variable written
with an operator then fails to read, with an error naming it; that needs an
ADIOS2 build that includes the operator (conda-forge, Spack or source); a
variable skipped silently hides that gap. Lossy operators (ZFP, SZ, MGARD) also
mean the stored values are approximations, which matters when comparing or
converting them.

## bpls

`bpls` comes with full ADIOS2 installs, not with the PyPI wheel.
`bpls -la name.bp` lists variables with types, shapes, step counts and
min/max (`-l`) plus attributes (`-a`); `-D` shows each variable's blocks;
`-d var` dumps values, bounded with `-s` (start) and `-c` (count).

## The adios tools

The clio-kit `adios` server reads BP4 and BP5 with `FileReader`/`Stream`:

- `list_bp5(directory)`: `.bp` and `.bp5` entries directly in one directory
  (not recursive).
- `inspect_variables(filename, variable_name?)`: type, shape and step count.
- `inspect_variables_at_step(filename, variable_name, step)`: one variable's
  metadata at one step.
- `inspect_attributes(filename, variable_name?)`: global or one variable's
  attributes with their values.
- `read_variable_at_step(filename, variable_name, target_step)`: the **whole**
  variable at that step as a flattened list plus its shape. There is no
  start/count, so it suits small variables; Python selects bounded parts of
  larger ones.

`filename` is the `.bp` directory path.
