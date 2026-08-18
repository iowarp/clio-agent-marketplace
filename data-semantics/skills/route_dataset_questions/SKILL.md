---
name: route_dataset_questions
title: Route Dataset Questions
description: Route dataset questions to HDF5, structure, analysis, or visualization experts.
---

Use this skill at the root of a data-semantics workflow. First preserve the
user goal and exact data handles. Delegate structure discovery before analysis
when the file surface is unknown.

Route any request naming an `.h5`, `.hdf5`, or NetCDF4 `.nc` file to `hdf5`.
Also route HDF5 layout, chunking, filters, attributes, VDS, SWMR, VOL, parallel
I/O, clio-core, IOWarp, CTE, CAE, or HDF5-ingest questions there even when no
file path is present. Do not route an HDF5 request to the generic `data` expert.

Route to analysis for statistics, quality, comparison, or derived claims. Route
to visualization only after the relevant variables and caveats are known.
