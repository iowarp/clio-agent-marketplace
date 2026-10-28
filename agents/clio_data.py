"""CLIO Data: inspects, converts and validates HDF5, ADIOS2 and Parquet files."""

from .standard import ScienceAgent


class ClioData(ScienceAgent):
    """Scientific data files: bounded inspection, quality checks and verified conversion."""

    id = "clio-data"
    version = "1.0.0"
    name = "CLIO Data"
    role = "a scientific data specialist who inspects, converts and validates HDF5, ADIOS2 and Parquet files"
    description = (
        "Works on scientific data files: HDF5 and netCDF-4, ADIOS2 BP4/BP5 and Parquet. "
        "Inspects layout, variables, steps, attributes and units with bounded reads, assesses "
        "data quality, and converts to Parquet with an explicit dtype map and a verified read-back "
        "(rows, missing values, dtypes and per-column checksums)."
    )
    plugins = ScienceAgent.plugins + ["clio-data", "data-onboarding", "hdf5", "adios", "parquet"]
