---
id: data-semantics.routing
section: domain
---
Route every HDF5-specific request to `hdf5`, including requests that name an
`.h5`, `.hdf5`, or NetCDF4 `.nc` file; ask about groups, datasets, chunks,
filters, attributes, VDS, SWMR, VOL, or parallel HDF5; or mention clio-core,
IOWarp, CTE, CAE, or HDF5 ingest. Do not send such a request to `data` merely
because it concerns a dataset. For a broader workflow, let `hdf5` establish the
file facts first, then start `analysis` or `visualization` only when the user
also needs downstream calculations or an artifact. `route-dataset-questions`
covers the full routing table.
