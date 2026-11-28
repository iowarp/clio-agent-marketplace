---
name: hdf5
title: HDF5
description: Use for HDF5 files (.h5, .hdf5, netCDF-4, NeXus, NWB, .h5ad) - contents, h5py reading and writing, chunking, compression, cloud access, parallel I/O and clio-core ingest.
---

# HDF5

This skill maps HDF5 questions to the reference guide that answers them.
`load_skill` loads a guide, for example
`load_skill("hdf5", file="references/chunking.md")`, or several at once with
`files=[...]`.

## What matters with HDF5 files

- **The file is the evidence.** An available file shows its real paths, shapes,
  dtypes, chunking and attributes; advice without looking at it rests on
  invented file facts.
- **HDF5 tools or h5py.** Without the tools, h5py through code execution does
  the same: `h5py.File(path, "r")` opens read-only, `list(f)` and `f.attrs` list
  contents, and slices such as `dset[:10]` sample values. Reading a whole large
  dataset just to look at it costs memory and time. The tools are described in
  "With the hdf5 tools" below.
- **Conventions locate the data.** The community convention an unfamiliar file
  follows tells where its primary data is: `references/conventions.md`.
- **Versions matter.** The guides describe HDF5 2.2 and h5py 3.16. Many
  behaviors and defaults changed in HDF5 2.0; in h5py,
  `h5py.version.hdf5_version` and `h5py.version.version` report what is
  installed.
- **Advice is not measurement.** Tuning advice is a recommendation unless it
  was measured.

## With the hdf5 tools

The `hdf5` MCP server keeps one file open at a time.

- **Which file.** A path the person gave identifies it. Without one,
  `list_available_hdf5_files` lists registered candidates; when there are
  several, which one is meant is the person's call, and choosing silently can
  open the wrong file.
- **Opening and walking.** `open_file` (mode `r` to inspect), then `list_keys`
  and `visit` for the hierarchy and `get_by_path` for one object.
- **Describing objects.** `get_shape`, `get_dtype`, `get_size`, `get_chunks`,
  `list_attributes` and `read_attribute`; `analyze_dataset_structure` gives a
  bounded overview.
- **Sampling values.** `read_partial_dataset`: `start` and `count` are
  comma-separated per dimension (`"0,0"`, `"10,10"`), and at most a thousand
  values come back, with truncation stated. `read_full_dataset` and
  `export_dataset` read the whole dataset into memory, which suits small ones.
- **I/O questions.** `identify_io_bottlenecks` reports static layout findings
  and `optimize_access_pattern` gives recommendations, not a benchmark; neither
  is measured performance.
- **Closing.** `close_file` releases the file the server holds open,
  including after a failed call.

The tools return the exact paths, dataset names, shapes, dtypes, chunks and
attributes; anything else is invented file facts. A failed tool call is
useful to the person when the answer names the failed operation, quotes the
useful part of its error, says what evidence is now missing, and offers a
concrete recovery step (another tool, h5py in a script, or a question for the
person).

`references/clio_core_ingest.md` covers ingest into clio-core, IOWarp or the
CTE/CAE, and "will clio-core make my reads faster". Its findings: bundling into
clio-core is not a single-client read speedup, its cost is per object (many
small datasets are best consolidated before any ingest), and it is for
cross-node sharing and tiering. The guide's figures are measurements of its
build, not of the person's system.
## Which guide

**What is in a file**

| Guide | Use for |
|---|---|
| `references/conventions.md` | Which community convention a file follows and where its main data is |
| `references/datatypes.md` | Compound, string, enum, variable-length and other datatypes; h5py type mapping |
| `references/dimension_scales.md` | Dimension scales and coordinate variables |
| `references/cf_compliance.md` | Whether a netCDF-4/HDF5 file meets the CF conventions |
| `references/region_references.md` | Object and region references |

**Layout and performance**

| Guide | Use for |
|---|---|
| `references/chunking.md` | Storage layout, chunk shape and the chunk cache |
| `references/filters.md` | Compression and other filters, and choosing among them |
| `references/io.md` | General I/O tuning: buffers, caches, access patterns |
| `references/file_space.md` | File size, free space, page allocation, repacking |

**Remote and cloud.** The guide depends on how the data is reached:
reading an existing file directly from S3 or HTTP is ROS3; going through a
service layer is HSDS; changing how a file is *written* so remote reads are
fast is the cloud-optimized guide.

| Guide | Use for |
|---|---|
| `references/ros3_vfd.md` | Reading HDF5 files directly from S3 or S3-compatible storage |
| `references/hsds.md` | HDF5 through the HSDS REST service (S3, Azure, POSIX backends) |
| `references/cloud_optimized.md` | Writing or rewriting files for efficient remote access |

**Concurrency and parallel I/O.** One writer with live readers is SWMR;
many MPI processes writing one file is parallel HDF5; at very large scale,
subfiling splits that file across subfiles.

| Guide | Use for |
|---|---|
| `references/swmr.md` | Single-writer/multiple-reader access to a file being written |
| `references/parallel.md` | MPI parallel HDF5 and collective I/O |
| `references/subfiling_vfd.md` | The subfiling driver for large-scale parallel writes |

**Drivers, connectors and virtual data**

| Guide | Use for |
|---|---|
| `references/core_vfd.md` | In-memory files with the core driver |
| `references/onion_vfd.md` | Revision history with the onion driver |
| `references/vds.md` | Virtual datasets that combine data from several files |
| `references/vol_usage.md` | VOL connectors such as async, cache, DAOS and REST |

**CLIO**

| Guide | Use for |
|---|---|
| `references/clio_core_ingest.md` | Whether to ingest an HDF5 file into clio-core or read it with h5py |
| `references/omni_selective.md` | OMNI configurations that load only the datasets a task needs |

Questions often span guides: a slow remote read may need `ros3_vfd.md` and
`chunking.md`; compression choices depend on `chunking.md` and
`filters.md`. Each guide whose topic the question touches is relevant.
