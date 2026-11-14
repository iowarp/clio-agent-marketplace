"""hdf5-ptc: HDF5 and NetCDF-4 files by handle, with cost before reading.

Every tool answers twice: a short text for the model, and structured content for a
``run_code`` script. ``read`` gives a script the whole array (``values="array"``) and the
model a summary, so a script computes on real data and the model's context holds only
what it needs. ``selection_cost`` prices a read from the chunk index before any data
moves, which matters when the file is in a linked source read by byte range.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any, Literal

import h5py
import numpy as np
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult
from mcp.types import TextContent
from pydantic import Field

from hdf5_ptc import arrays, cf, selection, writers
from hdf5_ptc.errors import refuse
from hdf5_ptc.handles import Handles, OpenFile

CALLER_META_KEY = "ai.iowarp.clio/caller"
PATHS_META_KEY = "ai.iowarp.clio/paths"
MAX_LIST = 500

mcp = FastMCP("h5", version="0.1.0")


def _typed(func):
    """Turn an unexpected failure into a typed refusal that says what failed and what to do."""
    import functools  # noqa: PLC0415

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except ToolError:
            raise
        except TimeoutError as exc:
            refuse(
                "read_timed_out",
                f"a read did not finish ({type(exc).__name__}); retry, or read fewer steps "
                "per call",
            )
        except OSError as exc:
            refuse("read_failed", f"{type(exc).__name__}: {exc or 'no detail'}")
        except Exception as exc:  # noqa: BLE001 - every failure is reported with its type
            refuse("tool_failed", f"{type(exc).__name__}: {exc or 'no detail'}")

    return wrapper


HANDLES = Handles()

Ints = Annotated[
    list[int] | int | None,
    Field(
        description="One integer per dimension (a bare number for a one-dimension dataset); "
        "omit for the default."
    ),
]


def _caller(ctx: Context | None) -> dict[str, str]:
    try:
        meta = ctx.request_context.meta if ctx is not None else None  # type: ignore[union-attr]
    except (AttributeError, LookupError, ValueError):
        return {}
    if meta is None:
        return {}
    data = meta.model_dump(by_alias=True) if hasattr(meta, "model_dump") else dict(meta)
    value = data.get(CALLER_META_KEY) or {}
    return {k: str(v) for k, v in value.items()} if isinstance(value, dict) else {}


def _owner(ctx: Context | None) -> str:
    return _caller(ctx).get("session") or "local"


def _paths(**decl: tuple[str, str]) -> dict[str, Any]:
    return {PATHS_META_KEY: {k: {"machine": m, "access": a} for k, (m, a) in decl.items()}}


def _result(text: str, payload: dict[str, Any]) -> ToolResult:
    return ToolResult(content=[TextContent(type="text", text=text)], structured_content=payload)


def _obj(f: OpenFile, path: str) -> h5py.HLObject:
    if path not in f.h5:
        refuse("path_not_found", f"{path} is not in {f.handle}; list_objects shows what is")
    return f.h5[path]


def _dataset(f: OpenFile, path: str) -> h5py.Dataset:
    obj = _obj(f, path)
    if not isinstance(obj, h5py.Dataset):
        refuse("not_a_dataset", f"{path} is a group; name a dataset inside it")
    return obj


def _mb(n: int | None) -> str:
    if n is None:
        return "unknown size"
    if n < 2**20:
        return f"{n / 1024:.1f} KB"
    if n < 2**30:
        return f"{n / 2**20:.1f} MB"
    return f"{n / 2**30:.2f} GB"


def _label(f: OpenFile) -> str:
    return Path(f.source.split("?", 1)[0]).name or f.handle


def _fetched(f: OpenFile) -> dict[str, int] | None:
    return f.fetched() if f.remote else None


def _dims_text(ds: h5py.Dataset) -> str:
    names = [d.get("name") or f"dim{d['axis']}" for d in cf.dimensions(ds)]
    return "(" + ", ".join(f"{n}={s}" for n, s in zip(names, ds.shape, strict=True)) + ")"


@mcp.tool(
    annotations={"title": "Open an HDF5 file", "readOnlyHint": True},
    meta=_paths(path=("local", "read")),
)
@_typed
def open_file(
    path: Annotated[
        str,
        Field(
            description="A local .h5/.hdf5/.nc path, or the byte-range URL CLIO returns for "
            "a file in a linked source (connected_data_open with range=true)."
        ),
    ],
    ctx: Context,
) -> ToolResult:
    """Open a file and return its handle. Many files can be open at once."""
    f = HANDLES.open(_owner(ctx), path)
    plist = f.h5.id.get_create_plist()
    try:
        strategy, _, _ = plist.get_file_space_strategy()
        page = plist.get_file_space_page_size() if strategy == h5py.h5f.FSPACE_STRATEGY_PAGE else 0
    except (AttributeError, RuntimeError, ValueError):
        strategy, page = None, 0
    paged = bool(page)
    roots = list(f.h5.keys())
    payload = {
        "handle": f.handle,
        "name": _label(f),
        "size": f.size,
        "remote": f.remote,
        "root_objects": roots[:MAX_LIST],
        "paged_metadata": paged,
        "page_size": page or None,
        "fetched": _fetched(f),
    }
    where = "by byte range" if f.remote else "locally"
    note = (
        ""
        if paged or not f.remote
        else (" Its metadata is not paged, so opening and walking it takes many small reads.")
    )
    text = (
        f"Opened {_label(f)} ({_mb(f.size)}) {where} as {f.handle}: "
        f"{len(roots)} objects at the root ({', '.join(roots[:12])}"
        f"{', ...' if len(roots) > 12 else ''}).{note}"
    )
    return _result(text, payload)


@mcp.tool(annotations={"title": "Close an HDF5 file", "readOnlyHint": True})
@_typed
def close_file(
    file: Annotated[str, Field(description="The handle open_file returned.")], ctx: Context
) -> ToolResult:
    """Close a file this session opened."""
    f = HANDLES.close(_owner(ctx), file)
    fetched = _fetched(f)
    extra = f"; {_mb(fetched['bytes'])} were read from it in total" if fetched else ""
    return _result(
        f"Closed {f.handle} ({_label(f)}){extra}.", {"closed": f.handle, "fetched": fetched}
    )


@mcp.tool(
    annotations={"title": "List objects in an HDF5 file", "readOnlyHint": True},
    meta=_paths(path=("none", "read")),
)
@_typed
def list_objects(
    file: Annotated[str, Field(description="The handle open_file returned.")],
    ctx: Context,
    path: Annotated[str, Field(description="A group inside the file.")] = "/",
    depth: Annotated[int, Field(description="1 lists the group's members; more walks deeper.")] = 1,
) -> ToolResult:
    """List groups and datasets under a group: shapes, types, dimensions, chunks, filters."""
    f = HANDLES.get(_owner(ctx), file)
    group = _obj(f, path)
    if not isinstance(group, h5py.Group):
        refuse("not_a_group", f"{path} is a dataset; describe it instead")
    rows: list[dict[str, Any]] = []
    base = group.name.rstrip("/")

    def visit(name: str, obj: Any) -> None:
        if len(rows) >= MAX_LIST or name.count("/") >= depth:
            return
        full = f"{base}/{name}"
        if isinstance(obj, h5py.Dataset):
            rows.append(
                {
                    "path": full,
                    "kind": "dataset",
                    "shape": list(obj.shape),
                    "dtype": str(obj.dtype),
                    "dims": [d.get("name") for d in cf.dimensions(obj)],
                    "chunks": list(obj.chunks) if obj.chunks else None,
                    "filters": selection._filters(obj),
                    "units": cf.plain(obj.attrs["units"]) if "units" in obj.attrs else None,
                    "long_name": cf.plain(obj.attrs["long_name"])
                    if "long_name" in obj.attrs
                    else None,
                }
            )
        elif isinstance(obj, h5py.Group):
            rows.append({"path": full, "kind": "group", "members": len(obj)})

    group.visititems(visit)
    lines = []
    for r in rows[:60]:
        if r["kind"] == "group":
            lines.append(f"{r['path']}/  group, {r['members']} members")
        else:
            unit = f" [{r['units']}]" if r.get("units") else ""
            chunks = f" chunks {tuple(r['chunks'])}" if r["chunks"] else " contiguous"
            dims = ", ".join(f"{n or '?'}={s}" for n, s in zip(r["dims"], r["shape"], strict=True))
            lines.append(
                f"{r['path']}  {r['dtype']} ({dims}){unit}{chunks} {' '.join(r['filters'])}"
            )
    more = f"\n... {len(rows) - 60} more in the structured result" if len(rows) > 60 else ""
    text = f"{len(rows)} objects under {path} in {_label(f)}:\n" + "\n".join(lines) + more
    return _result(text, {"file": f.handle, "path": path, "objects": rows, "fetched": _fetched(f)})


@mcp.tool(
    annotations={"title": "Describe an HDF5 object", "readOnlyHint": True},
    meta=_paths(path=("none", "read")),
)
@_typed
def describe(
    file: Annotated[str, Field(description="The handle open_file returned.")],
    path: Annotated[str, Field(description="A dataset or group inside the file.")],
    ctx: Context,
) -> ToolResult:
    """One object in full: dimensions and coordinates, layout, filters, attributes and units."""
    f = HANDLES.get(_owner(ctx), file)
    obj = _obj(f, path)
    attrs = cf.attributes(obj)
    if isinstance(obj, h5py.Group):
        payload = {
            "path": obj.name,
            "kind": "group",
            "members": list(obj.keys())[:MAX_LIST],
            "attributes": attrs,
        }
        return _result(
            f"{obj.name}: group with {len(obj)} members; {len(attrs)} attributes.", payload
        )
    full = selection.parse(obj)
    price = selection.cost(obj, full) if obj.ndim else {}
    dims = cf.dimensions(obj)
    meaning = cf.meaning(obj)
    payload = {
        "path": obj.name,
        "kind": "dataset",
        "shape": list(obj.shape),
        "dtype": str(obj.dtype),
        "dimensions": dims,
        "chunks": list(obj.chunks) if obj.chunks else None,
        "filters": selection._filters(obj),
        "stored_bytes": int(obj.id.get_storage_size()),
        "meaning": meaning,
        "attributes": attrs,
        "full_read": price,
    }
    unit = meaning.get("units")
    packing = [
        k for k in ("scale_factor", "add_offset", "_FillValue", "missing_value") if k in meaning
    ]
    chunk_txt = (
        f"chunks {tuple(obj.chunks)} ({_mb(price.get('chunk_bytes'))} each before compression)"
        if obj.chunks
        else "contiguous"
    )
    text = (
        f"{obj.name}: {obj.dtype} {_dims_text(obj)}"
        + (f", units {unit}" if unit else "")
        + (f", {meaning['long_name']}" if "long_name" in meaning else "")
        + f". {chunk_txt}, filters {', '.join(payload['filters']) or 'none'}; "
        f"{_mb(payload['stored_bytes'])} stored. "
        + (f"Reads apply {', '.join(packing)} (fill values become NaN). " if packing else "")
        + "Coordinates: "
        + ", ".join(f"{d.get('name') or d['axis']}={d.get('coordinate') or 'index'}" for d in dims)
        + "."
    )
    return _result(text, payload)


@mcp.tool(
    annotations={"title": "Price a read", "readOnlyHint": True},
    meta=_paths(path=("none", "read")),
)
@_typed
def selection_cost(
    file: Annotated[str, Field(description="The handle open_file returned.")],
    path: Annotated[str, Field(description="A dataset inside the file.")],
    ctx: Context,
    start: Ints = None,
    count: Ints = None,
    step: Ints = None,
) -> ToolResult:
    """What a read would move, from the chunk index alone: chunks touched and stored bytes."""
    f = HANDLES.get(_owner(ctx), file)
    ds = _dataset(f, path)
    sel = selection.parse(ds, start, count, step)
    price = selection.cost(ds, sel)
    share = price["stored_bytes"] / f.size if f.size else None
    text = (
        f"Reading {path}[{sel.as_dict()}] ({sel.size:,} values, {_mb(price['selection_bytes'])}) "
        f"touches {price['chunks_touched']} chunk(s) holding {_mb(price['stored_bytes'])} stored"
        + (f" ({share:.1%} of the file)" if share is not None else "")
        + (
            f", {_mb(price.get('decoded_bytes'))} once decoded"
            if price.get("decoded_bytes")
            else ""
        )
        + ("" if price.get("exact", True) else "; estimated from a sample of the index")
        + "."
    )
    return _result(
        text,
        {"file": f.handle, "path": path, "selection": sel.as_dict(), **price, "file_share": share},
    )


@mcp.tool(
    annotations={"title": "Read part of a dataset", "readOnlyHint": True},
    meta=_paths(path=("none", "read")),
)
@_typed
def read(
    file: Annotated[str, Field(description="The handle open_file returned.")],
    path: Annotated[str, Field(description="A dataset inside the file.")],
    ctx: Context,
    start: Ints = None,
    count: Ints = None,
    step: Ints = None,
    values: Annotated[
        Literal["summary", "array"],
        Field(
            description="summary: statistics and the first values. array: the whole selection "
            "as an array, for a run_code script only (hdf5.read in the kernel decodes it)."
        ),
    ] = "summary",
    decode: Annotated[bool, Field(description="Apply CF packing; fill values become NaN.")] = True,
) -> ToolResult:
    """Read a hyperslab. The model gets a summary; a script can get the whole array."""
    if values == "array" and _caller(ctx).get("via") == "direct":
        refuse(
            "array_values_need_code_caller",
            "a whole array is for a run_code script; called directly, use values='summary' "
            "or reduce",
        )
    f = HANDLES.get(_owner(ctx), file)
    ds = _dataset(f, path)
    sel = selection.parse(ds, start, count, step)
    data = selection.read(ds, sel, decode=decode)
    summary = arrays.stats(data)
    payload: dict[str, Any] = {
        "file": f.handle,
        "path": path,
        "selection": sel.as_dict(),
        "shape": list(data.shape),
        "dtype": str(data.dtype),
        "stats": summary,
        "fetched": _fetched(f),
    }
    if values == "array":
        payload["array"] = arrays.encode(data)
    missing = summary.get("values", 0) - summary.get("finite", summary.get("values", 0))
    stats_txt = ", ".join(f"{k} {v:.6g}" for k, v in summary.items() if isinstance(v, float))
    head = arrays.first_values(data)
    text = (
        f"Read {path} {list(data.shape)} {data.dtype}"
        + (f": {stats_txt}" if stats_txt else "")
        + f"; {missing:,} not finite."
        + (
            " The whole array is in the structured result."
            if values == "array"
            else f" First {len(head)} of {data.size:,} values: {json.dumps(head)}"
        )
    )
    return _result(text, payload)


@mcp.tool(
    annotations={"title": "Reduce a dataset", "readOnlyHint": True},
    meta=_paths(path=("none", "read")),
)
@_typed
def reduce(
    file: Annotated[str, Field(description="The handle open_file returned.")],
    path: Annotated[str, Field(description="A dataset inside the file.")],
    ctx: Context,
    ops: Annotated[
        list[str],
        Field(description="Any of min, max, mean, sum, std, count, argmin, argmax."),
    ],
    start: Ints = None,
    count: Ints = None,
    step: Ints = None,
    over: Annotated[
        list[int] | None,
        Field(
            description="Axes to reduce over; omit for all. The other axes give one row per "
            "index, e.g. over the spatial axes to get one row per time step."
        ),
    ] = None,
) -> ToolResult:
    """Exact statistics over a selection, with argmin/argmax located in coordinates."""
    f = HANDLES.get(_owner(ctx), file)
    ds = _dataset(f, path)
    sel = selection.parse(ds, start, count, step)
    if sel.size * max(ds.dtype.itemsize, 4) > arrays.REDUCE_LIMIT:
        refuse(
            "selection_too_large_to_reduce",
            f"{sel.size:,} values; reduce a smaller selection or use a step",
        )
    data = selection.read(ds, sel, decode=True)
    result = arrays.reduce(ds, sel, data, ops, over)
    rows = result["rows"]
    lines = [json.dumps(r, default=str) for r in rows[:24]]
    more = f"\n... {len(rows) - 24} more rows in the structured result" if len(rows) > 24 else ""
    text = f"{path} {', '.join(ops)} over axes {result['over']}:\n" + "\n".join(lines) + more
    return _result(
        text,
        {
            "file": f.handle,
            "path": path,
            "selection": sel.as_dict(),
            **result,
            "fetched": _fetched(f),
        },
    )


@mcp.tool(
    annotations={"title": "Write a subset file", "readOnlyHint": False},
    meta=_paths(out_path=("local", "write")),
)
@_typed
def write_subset(
    file: Annotated[str, Field(description="The handle open_file returned.")],
    items: Annotated[
        list[dict[str, Any]],
        Field(
            description="Datasets to write: [{path, start?, count?, step?, name?}]. "
            "For format vtk, exactly one 3D or (time, z, y, x) item."
        ),
    ],
    out_path: Annotated[
        str,
        Field(description="netcdf: a .nc file path. vtk: a folder for the .vtr series and .pvd."),
    ],
    ctx: Context,
    format: Annotated[Literal["netcdf", "vtk"], Field(description="Output format.")] = "netcdf",
    vertical: Annotated[
        dict[str, float] | None,
        Field(
            description="vtk only: map the vertical coordinate to z = scale * ln(reference / "
            "value), e.g. {reference: 1000, scale: 7} for log-pressure height in km."
        ),
    ] = None,
) -> ToolResult:
    """Write selections to a new file with their coordinates, attributes and provenance."""
    f = HANDLES.get(_owner(ctx), file)
    if not items:
        refuse("subset_empty", "name at least one dataset")
    out = Path(out_path).expanduser()
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        refuse("out_path_invalid", f"{out.parent} cannot be created: {exc}")
    resolved = []
    for item in items:
        ds = _dataset(f, str(item.get("path", "")))
        sel = selection.parse(ds, item.get("start"), item.get("count"), item.get("step"))
        resolved.append((ds, sel, str(item.get("name") or ds.name.rsplit("/", 1)[-1])))
    source = _label(f)
    if format == "vtk":
        if len(resolved) != 1:
            refuse("vtk_needs_one_item", "write one variable per VTK series")
        ds, sel, name = resolved[0]
        written = writers.write_vtk_series(ds, sel, out, name, vertical)
        b = written["bounds"]
        spans = [b[1] - b[0], b[3] - b[2], b[5] - b[4]]
        text = (
            f"Wrote {name} as {written['steps']} VTK step(s) on a {written['grid']} grid "
            f"to {written['path']} (range {written['range'][0]:.4g} to {written['range'][1]:.4g}). "
            f"The box spans {spans[0]:.3g} x {spans[1]:.3g} x {spans[2]:.3g} (x, y, z)"
            + (
                "; it is much taller than it is wide, so in a 3D view the field is a thin "
                "column: fewer levels or a smaller vertical scale flattens it."
                if spans[2] > 1.5 * max(spans[0], spans[1])
                else "."
            )
        )
        if written["steps"] > 1:
            first, last = written["times"][0], written["times"][-1]
            when = (
                f" ({written['times_iso'][0]} to {written['times_iso'][-1]})"
                if written.get("times_iso")
                else ""
            )
            text += (
                f" Its time steps are the file's own time values, {first:.10g} to {last:.10g}"
                + (f" {written['time_units']}" if written.get("time_units") else "")
                + f"{when}: a table or chart column holding the same values links to it by time."
            )
    else:
        written = writers.write_netcdf(resolved, out, source)
        text = (
            f"Wrote {len(written['variables'])} variable(s) to {written['path']} with provenance."
        )
    return _result(text, {"file": f.handle, **written, "fetched": _fetched(f)})


def main() -> None:
    """Run the server over stdio."""
    np.seterr(all="ignore")
    os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
    mcp.run()


if __name__ == "__main__":
    main()
