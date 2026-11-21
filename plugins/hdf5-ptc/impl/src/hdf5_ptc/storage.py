"""Only the opened file's own bytes are read.

HDF5 can take an object's contents from other files: an external link opens another
HDF5 file, a dataset with external storage reads raw bytes from any file it names, and
a virtual dataset maps other files' datasets into its own. A file someone else wrote
could name any file on this computer that way, so this server refuses all three.
"""

from __future__ import annotations

import h5py

from hdf5_ptc.errors import refuse


def in_file(obj: h5py.HLObject, root: h5py.File) -> h5py.HLObject:
    """``obj`` if HDF5 reached it, and reads its values, within ``root``; else refuse."""
    if obj.file.filename != root.filename:
        refuse(
            "outside_the_file",
            f"{obj.name} is an external link to {obj.file.filename}; "
            "open that file itself if the person wants it read",
        )
    if isinstance(obj, h5py.Dataset):
        if obj.external:
            refuse(
                "outside_the_file",
                f"{obj.name} keeps its values in other files (HDF5 external storage), "
                "which this server does not read",
            )
        if obj.is_virtual and any(s.file_name != "." for s in obj.virtual_sources()):
            refuse(
                "outside_the_file",
                f"{obj.name} is a virtual dataset mapped from other files, "
                "which this server does not read",
            )
    return obj
