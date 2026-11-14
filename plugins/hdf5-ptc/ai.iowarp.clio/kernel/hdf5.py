"""``hdf5``: HDF5 and NetCDF-4 files from a script, read as NumPy arrays.

Every call is async: ``await`` each one (top-level ``await`` works in run_code).

    f = await hdf5.open("/data/run.nc")            # a local path, or a range URL from
                                                   # connected_data_open(range=True)
    print(await f.describe("/T"))                  # dims, units, chunks, packing
    print(await f.cost("/T", start=[0, 0, 220, 1040], count=[1, 37, 80, 120]))
    t = await f.read("/T", start=[0, 0, 220, 1040], count=[1, 37, 80, 120])
    print(t.shape, float(t.max()))                 # a numpy array; fills are NaN
    rows = await f.reduce("/P", ops=["min", "argmin"], over=[1, 2])   # per time step
    await f.close()

``read`` returns the whole selection as an array (NumPy must be importable in the kernel);
a selection over the server's inline cap is refused with ``selection_exceeds_inline_cap``,
so read it in parts. ``cost`` prices a read from the chunk index before any data moves:
check it first for files in a linked source. Errors are ``ToolError`` with the server's
reason first (``path_not_found``, ``selection_out_of_bounds``, ``unknown_handle``).
"""

from __future__ import annotations

import base64
import importlib
from typing import Any


async def _call(name: str, **args: Any) -> Any:
    return await tools.call(name, **args)  # noqa: F821 - bound by the kernel


def _array(payload: dict[str, Any]) -> Any:
    try:
        np = importlib.import_module("numpy")
    except ImportError as exc:  # the kernel's Python has no NumPy
        raise ToolError("numpy_unavailable: this kernel's Python has no NumPy") from exc  # noqa: F821
    raw = base64.b64decode(payload["data"])
    return np.frombuffer(raw, dtype=payload["dtype"]).reshape(payload["shape"]).copy()


def _sel(start: Any, count: Any, step: Any) -> dict[str, Any]:
    out = {}
    for key, value in (("start", start), ("count", count), ("step", step)):
        if value is not None:
            out[key] = [int(v) for v in value]
    return out


class File:
    """An open file; every method is one call to the hdf5-ptc server."""

    def __init__(self, handle: str, info: dict[str, Any]) -> None:
        self.handle = handle
        self.info = info

    def __repr__(self) -> str:
        return f"<hdf5.File {self.handle} {self.info.get('name')}>"

    async def objects(self, path: str = "/", depth: int = 1) -> list[dict[str, Any]]:
        """Groups and datasets under ``path``: shape, dtype, dims, chunks, units."""
        out = await _call("h5_list_objects", file=self.handle, path=path, depth=depth)
        return out["objects"]

    async def describe(self, path: str) -> dict[str, Any]:
        """One object in full: dimensions, coordinates, attributes, layout, packing."""
        return await _call("h5_describe", file=self.handle, path=path)

    async def cost(self, path: str, start=None, count=None, step=None) -> dict[str, Any]:
        """Chunks touched and stored bytes a read would move (no data is read)."""
        return await _call(
            "h5_selection_cost", file=self.handle, path=path, **_sel(start, count, step)
        )

    async def read(self, path: str, start=None, count=None, step=None, decode=True) -> Any:
        """The selection as a NumPy array (CF packing applied, fill values as NaN)."""
        out = await _call(
            "h5_read",
            file=self.handle,
            path=path,
            values="array",
            decode=decode,
            **_sel(start, count, step),
        )
        return _array(out["array"])

    async def coords(self, path: str) -> dict[str, Any]:
        """Each axis's coordinate values as arrays, by dimension name."""
        info = await self.describe(path)
        out = {}
        for dim in info["dimensions"]:
            name = dim.get("name") or f"dim{dim['axis']}"
            out[name] = await self.read(dim["coordinate"]) if dim.get("coordinate") else None
        return out

    async def reduce(
        self, path: str, ops: list[str], start=None, count=None, step=None, over=None
    ) -> list[dict[str, Any]]:
        """Exact statistics; ``over`` names the axes reduced, one row per kept index."""
        args = {"file": self.handle, "path": path, "ops": list(ops), **_sel(start, count, step)}
        if over is not None:
            args["over"] = [int(a) for a in over]
        return (await _call("h5_reduce", **args))["rows"]

    async def write_subset(self, items: list[dict[str, Any]], out_path: str, **kw: Any) -> Any:
        """Write selections to a new NetCDF-4 file (or a VTK series with format='vtk')."""
        return await _call(
            "h5_write_subset", file=self.handle, items=items, out_path=out_path, **kw
        )

    async def close(self) -> None:
        await _call("h5_close_file", file=self.handle)


class _Hdf5:
    async def open(self, path: str) -> File:
        """Open a local file or a range URL and return a :class:`File`."""
        info = await _call("h5_open_file", path=path)
        return File(info["handle"], info)


export = _Hdf5()
