"""Arrays for scripts, summaries for the model, and exact reductions.

A model reads a bounded summary: shape, statistics and the first values. A ``run_code``
script reads the whole array, encoded once as little-endian bytes in base64, and the
plugin's kernel binding turns it back into a NumPy array.
"""

from __future__ import annotations

import base64
import itertools
import math
import os
from typing import Any

import h5py
import numpy as np

from hdf5_ptc import cf
from hdf5_ptc.errors import refuse
from hdf5_ptc.selection import Selection

#: The most values a summary prints for the model.
SUMMARY_VALUES = 24
#: Largest array returned inline to a script (bytes of raw values).
INLINE_LIMIT_ENV = "HDF5_PTC_INLINE_MAX_BYTES"
DEFAULT_INLINE_LIMIT = 16 * 2**20
#: Largest decoded selection a reduction loads at once.
REDUCE_LIMIT = 2 * 2**30
#: Most rows a reduction returns (one per kept index).
MAX_ROWS = 10_000
OPS = ("min", "max", "mean", "sum", "std", "count", "argmin", "argmax")


def inline_limit() -> int:
    try:
        return int(os.environ.get(INLINE_LIMIT_ENV, DEFAULT_INLINE_LIMIT))
    except ValueError:
        return DEFAULT_INLINE_LIMIT


def stats(data: np.ndarray) -> dict[str, Any]:
    """min, max, mean and counts of the finite values (empty when there are none)."""
    if data.dtype.kind not in "iuf" or data.size == 0:
        return {"values": int(data.size)}
    finite = np.isfinite(data) if data.dtype.kind == "f" else np.ones(data.shape, bool)
    n = int(finite.sum())
    out: dict[str, Any] = {"values": int(data.size), "finite": n}
    if n:
        vals = data[finite]
        out.update(min=float(vals.min()), max=float(vals.max()), mean=float(vals.mean()))
    return out


def first_values(data: np.ndarray, n: int = SUMMARY_VALUES) -> list[Any]:
    flat = data.ravel()[:n]
    return [None if isinstance(v, float) and math.isnan(v) else v for v in flat.tolist()]


def encode(data: np.ndarray) -> dict[str, Any]:
    """The array as ``{shape, dtype, order, encoding, data}`` for a script."""
    if data.dtype.kind not in "iufb":
        refuse("dtype_not_array", f"{data.dtype} values cannot be returned as a numeric array")
    little = data.astype(data.dtype.newbyteorder("<"), copy=False)
    raw = np.ascontiguousarray(little).tobytes()
    if len(raw) > inline_limit():
        refuse(
            "selection_exceeds_inline_cap",
            f"the selection is {len(raw):,} bytes; at most {inline_limit():,} come back in one "
            "call. Read it in parts (a smaller count, a step, or one index at a time).",
        )
    return {
        "shape": list(data.shape),
        "dtype": little.dtype.str,
        "order": "C",
        "encoding": "base64-le",
        "data": base64.b64encode(raw).decode("ascii"),
    }


def _axes(over: Any, rank: int) -> tuple[int, ...]:
    if over is None:
        return tuple(range(rank))
    try:
        axes = tuple(sorted({int(a) % rank for a in over}))
    except (TypeError, ValueError, ZeroDivisionError):
        refuse("reduce_invalid", "over must list axis numbers")
    return axes


def _nan_op(name: str, data: np.ndarray, axes: tuple[int, ...]) -> np.ndarray:
    with np.errstate(all="ignore"):
        if name == "min":
            return np.nanmin(data, axis=axes)
        if name == "max":
            return np.nanmax(data, axis=axes)
        if name == "mean":
            return np.nanmean(data, axis=axes)
        if name == "sum":
            return np.nansum(data, axis=axes)
        if name == "std":
            return np.nanstd(data, axis=axes)
        if name == "count":
            return np.isfinite(data).sum(axis=axes)
    raise AssertionError(name)


def reduce(
    dataset: h5py.Dataset,
    sel: Selection,
    data: np.ndarray,
    ops: list[str],
    over: Any,
) -> dict[str, Any]:
    """Exact reductions of ``data`` (the decoded selection) over the ``over`` axes.

    ``argmin``/``argmax`` are reported as dataset indexes and coordinate values. With
    ``over`` naming only some axes, there is one row per index of the kept axes.
    """
    unknown = [op for op in ops if op not in OPS]
    if unknown:
        refuse("reduce_invalid", f"unknown ops {unknown}; choose from {list(OPS)}")
    rank = data.ndim
    axes = _axes(over, rank)
    kept = tuple(a for a in range(rank) if a not in axes)
    data = data.astype(np.float64, copy=False) if data.dtype.kind in "iub" else data
    n_rows = math.prod(data.shape[a] for a in kept) if kept else 1
    if n_rows > MAX_ROWS:
        refuse("reduce_too_many_rows", f"{n_rows} rows; reduce over more axes (at most {MAX_ROWS})")
    moved = np.moveaxis(data, kept + axes, tuple(range(rank))) if kept else data
    flat = moved.reshape((n_rows, -1)) if rank else moved.reshape((1, 1))
    rows = []
    kept_ranges = [range(data.shape[a]) for a in kept]
    for r, kept_idx in enumerate(itertools.product(*kept_ranges) if kept else [()]):
        values = flat[r]
        row: dict[str, Any] = {}
        finite = np.isfinite(values)
        for op in ops:
            if op in ("argmin", "argmax"):
                if not finite.any():
                    row[op] = None
                    continue
                masked = np.where(finite, values, np.inf if op == "argmin" else -np.inf)
                pos = int(np.argmin(masked) if op == "argmin" else np.argmax(masked))
                inner = np.unravel_index(pos, tuple(data.shape[a] for a in axes)) if axes else ()
                local = [0] * rank
                for a, i in zip(kept, kept_idx, strict=True):
                    local[a] = i
                for a, i in zip(axes, inner, strict=True):
                    local[a] = int(i)
                index = tuple(s + i * k for s, i, k in zip(sel.start, local, sel.step, strict=True))
                row[op] = {
                    "value": float(values[pos]),
                    "index": list(index),
                    "at": cf.coordinate_values(dataset, index),
                }
            else:
                with np.errstate(all="ignore"):
                    v = _nan_op(op, values[None, :], (1,))[0]
                row[op] = None if (isinstance(v, float) and math.isnan(v)) else v.item()
        if kept:
            index = [
                s + i * k
                for s, i, k in zip(
                    (sel.start[a] for a in kept), kept_idx, (sel.step[a] for a in kept), strict=True
                )
            ]
            full = [0] * rank
            for a, i in zip(kept, index, strict=True):
                full[a] = i
            coords = cf.coordinate_values(dataset, tuple(full))
            names = [d.get("name") or f"dim{d['axis']}" for d in cf.dimensions(dataset)]
            row = {"index": index, **{names[a]: coords[names[a]] for a in kept}, **row}
        rows.append(row)
    return {"over": list(axes), "kept": list(kept), "rows": rows}
