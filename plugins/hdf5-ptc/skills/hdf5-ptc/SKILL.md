---
name: hdf5-ptc
title: HDF5 in scripts
description: Use to explore or analyse HDF5 and NetCDF-4 files (.h5, .hdf5, .nc, .nc4), local or in a linked source - walking the structure, pricing a read before it moves data, computing statistics over slices, and writing subsets for charts, maps or 3D views.
keywords: [hdf5, netcdf, h5, chunking, hyperslab, run_code, level:L1]
---

# HDF5 in scripts

The `h5` tools open files by **handle**: `open_file` returns one, every other tool
takes it as `file`, and several files can be open at once. Close what you open.

## Order of work

1. **Structure before values.** `list_objects` then `describe` the datasets you
   need: dimension names and their coordinate variables, units, chunk shape,
   filters, and the attributes that change the numbers (`scale_factor`,
   `add_offset`, `_FillValue`). Reads apply the packing and turn fill values into
   NaN, so report physical units, not stored integers.
2. **Price before reading.** `selection_cost` reads only the chunk index and says
   how many chunks a selection touches and how many stored bytes that is. A chunk
   is read whole: a small box inside a large chunk still moves the chunk. Say what
   a read will cost before a large or remote one, and choose selections that align
   with the chunks (fewer time steps, a step along an axis) when the cost is high.
3. **Compute in a script.** Inside `run_code`, the `hdf5` binding returns real
   NumPy arrays: `f = await hdf5.open(path)`, `a = await f.read(path, start=...,
   count=...)`. Loop over time steps or files there, so many reads cost one model
   step. Called directly, `read` gives a summary only; use `reduce` for exact
   minima, maxima and means with their locations in coordinates (`over` the
   spatial axes gives one row per time step).
4. **Locate in coordinates.** Report positions as coordinate values (latitude,
   longitude, level, time), which `reduce` and `describe` give, not array indexes.

## Files in a linked source

A file in a linked source is not on disk. Ask `connected_data_open` for it with
`range=true`; it returns a byte-range URL that `open_file` and `hdf5.open` accept.
Only the bytes a read touches move, so pricing first matters most here. If the
source cannot serve ranges, say so and give the file's size before downloading.

## Results for others

`write_subset` writes the selections you used to a new NetCDF-4 file, with
coordinates, attributes and the source selection as provenance; register it so a
chart, map or table can read it. For a 3D view of a (time, level, y, x) field, write
`format="vtk"`: a rectilinear grid per step with a time index, which ParaView opens
with real axes. Uneven vertical levels can be mapped with `vertical` (for pressure,
`{reference, scale}` gives log-pressure height). Its time steps are the file's own time
values, so a table or chart column holding the same values links it to the other
views by time; keep the source's time values in the tables you write.

## Errors

Errors name a reason first (`selection_out_of_bounds`, `selection_exceeds_inline_cap`,
`unknown_handle`, `range_unsupported`). Say which call failed, what that leaves
unknown, and the next step: a smaller selection, a step, or another tool. For format
questions (conventions, chunking, filters, cloud layouts), the `hdf5` skill's
reference guides answer them.
