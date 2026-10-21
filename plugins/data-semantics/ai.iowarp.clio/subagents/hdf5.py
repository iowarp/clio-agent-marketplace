"""HDF5 Expert: a defined subagent of data-semantics."""

from clio_agent.sdk import PromptFile, Subagent

hdf5 = Subagent(
    "hdf5",
    prompt=PromptFile("prompt/subagents/hdf5.md"),
    description="Answers HDF5 questions — layout, chunking, filters, compression, and I/O performance — and decides when and how to route an HDF5 file through clio-core (the CTE blob store via the CAE assimilator) versus reading it natively with h5py. Route any HDF5 file-format, ingest, or 'should I use clio-core / IOWarp' question here.",
    plugins=["hdf5"],
    tools=["hdf5_list_available_hdf5_files", "hdf5_open_file", "hdf5_close_file", "hdf5_list_keys", "hdf5_visit", "hdf5_get_by_path", "hdf5_get_shape", "hdf5_get_dtype", "hdf5_get_size", "hdf5_get_chunks", "hdf5_read_partial_dataset", "hdf5_list_attributes", "hdf5_read_attribute", "hdf5_analyze_dataset_structure", "hdf5_identify_io_bottlenecks", "hdf5_optimize_access_pattern", "load_skill"],
)
