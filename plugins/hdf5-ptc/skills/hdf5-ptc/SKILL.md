---
name: hdf5-ptc
title: HDF5 in scripts
description: Use to explore or analyse HDF5 and NetCDF-4 files (.h5, .hdf5, .nc, .nc4), local or in a linked source - walking the structure, pricing a read before it moves data, computing statistics over slices, and writing subsets for charts, maps or 3D views.
keywords: [hdf5, netcdf, h5, chunking, hyperslab, run_code, level:L1]
---

# HDF5 in scripts

The `h5` tools open files by **handle**: `open_file` returns one, every other tool
takes it as `file`, and several files can be open at once. A handle stays open
until it is closed.

## How the tools fit together

- **Structure.** `list_objects` and `describe` give the datasets' dimension names
  and their coordinate variables, units, chunk shape, filters, and the attributes
  that change the numbers (`scale_factor`, `add_offset`, `_FillValue`). Reads
  apply the packing and turn fill values into NaN, so values come back in
  physical units, not stored integers.
- **Cost of a read.** `selection_cost` reads only the chunk index and says how
  many chunks a selection touches and how many stored bytes that is. A chunk is
  read whole: a small box inside a large chunk still moves the chunk. A large or
  remote read's cost is worth knowing before it moves data, and selections that
  align with the chunks (fewer time steps, a step along an axis) cost less.
- **Computing in a script.** Inside `run_code`, the `hdf5` binding returns real
  NumPy arrays: `f = await hdf5.open(path)`, `a = await f.read(path, start=...,
  count=...)`. Loops over time steps or files there cost one model step for many
  reads. Called directly, `read` gives a summary only; `reduce` gives exact
  minima, maxima and means with their locations in coordinates (`over` the
  spatial axes gives one row per time step).
- **Coordinates, not indexes.** `reduce` and `describe` give positions as
  coordinate values (latitude, longitude, level, time), which mean something to
  a reader; array indexes do not.

A `workspace-file:` link with `?locator=/path/in/file` opens the file's viewer on
that dataset, so a table of variables can be a list of fields the reader opens
with one click.

## Files in a linked source

A file in a linked source is not on disk. `connected_data_open` with `range=true`
returns a byte-range URL that `open_file` and `hdf5.open` accept. Only the bytes
a read touches move, so the cost of a read matters most here. A source that
cannot serve ranges means a full download of the file's size.

## Results for others

`write_subset` writes the selections used to a new NetCDF-4 file, with
coordinates, attributes and the source selection as provenance; once registered,
a chart, map or table can read it. For a 3D view of a (time, level, y, x) field,
`format="vtk"` writes a rectilinear grid per step with a time index, which
ParaView opens with real axes. Several variables on the same box and times go
into one series as separate fields, even from different files (an item can name
another open `file`), so one view can show, say, liquid and ice together. Uneven
vertical levels can be mapped with `vertical` (for pressure, `{reference, scale}`
gives log-pressure height). Its time steps are the file's own time values, so a
table or chart column holding the same values links it to the other views by
time; tables that keep the source's time values stay linked.

## Errors

Errors name a reason first (`selection_out_of_bounds`, `selection_exceeds_inline_cap`,
`unknown_handle`, `range_unsupported`). Which call failed, what that leaves
unknown, and a next step (a smaller selection, a step, or another tool) are what
the person needs from a failure. For format questions (conventions, chunking,
filters, cloud layouts), the `hdf5` skill's reference guides answer them.