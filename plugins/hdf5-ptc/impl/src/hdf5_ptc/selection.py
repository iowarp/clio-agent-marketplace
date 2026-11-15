"""Hyperslab selections: parse them, price them from the chunk index, read them decoded.

A selection is ``start``, ``count`` and an optional ``step`` per dimension (missing
``start`` is all zeros, missing ``count`` is the rest of each dimension). Pricing reads
only the chunk index: which chunks the selection touches and their stored (compressed)
size, which is what a remote read has to move.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Any

import h5py
import numpy as np

from hdf5_ptc.errors import refuse

#: Above this many touched chunks the cost is estimated from a sample of the index.
EXACT_CHUNK_LIMIT = 20_000


@dataclass(frozen=True)
class Selection:
    """A strided hyperslab of one dataset."""

    start: tuple[int, ...]
    count: tuple[int, ...]
    step: tuple[int, ...]

    @property
    def shape(self) -> tuple[int, ...]:
        return self.count

    @property
    def size(self) -> int:
        return math.prod(self.count)

    def slices(self) -> tuple[slice, ...]:
        return tuple(
            slice(s, s + (c - 1) * k + 1, k)
            for s, c, k in zip(self.start, self.count, self.step, strict=True)
        )

    def last(self) -> tuple[int, ...]:
        return tuple(
            s + (c - 1) * k for s, c, k in zip(self.start, self.count, self.step, strict=True)
        )

    def as_dict(self) -> dict[str, list[int]]:
        return {"start": list(self.start), "count": list(self.count), "step": list(self.step)}


def _ints(value: Any, name: str, rank: int) -> list[int] | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = [v for v in value.replace(" ", "").split(",") if v]
    elif isinstance(value, int) and rank == 1:
        value = [value]  # one axis: a bare number is that axis's value
    try:
        out = [int(v) for v in value]
    except (TypeError, ValueError):
        refuse("selection_invalid", f"{name} must be a list of {rank} integers")
    if len(out) != rank:
        meaning = {
            "start": "the first index along each axis",
            "count": "how many values along each axis",
            "step": "the stride along each axis (1 takes every value)",
        }.get(name, "one value per axis")
        refuse(
            "selection_invalid",
            f"{name} has {len(out)} values; the dataset has {rank} dims. {name} is {meaning}",
        )
    return out


def parse(
    dataset: h5py.Dataset, start: Any = None, count: Any = None, step: Any = None
) -> Selection:
    """The selection ``start``/``count``/``step`` describes in ``dataset``, validated."""
    shape = dataset.shape
    rank = len(shape)
    if rank == 0:
        return Selection((), (), ())
    s = _ints(start, "start", rank) or [0] * rank
    k = _ints(step, "step", rank) or [1] * rank
    if any(v < 1 for v in k):
        refuse("selection_invalid", "every step must be at least 1")
    c = _ints(count, "count", rank) or [
        max(0, math.ceil((n - a) / b)) for n, a, b in zip(shape, s, k, strict=True)
    ]
    for dim, (n, a, b, m) in enumerate(zip(shape, s, c, k, strict=True)):
        if a < 0 or a >= n:
            refuse("selection_out_of_bounds", f"start[{dim}]={a} is outside 0..{n - 1}")
        if b < 1 or a + (b - 1) * m >= n:
            refuse(
                "selection_out_of_bounds",
                f"dim {dim}: start {a}, count {b}, step {m} reaches index {a + (b - 1) * m}, past "
                f"its length {n}. count is the number of values taken, so at most "
                f"{(n - 1 - a) // m + 1} here",
            )
    return Selection(tuple(s), tuple(c), tuple(k))


def _touched(first: int, last: int, step: int, chunk: int) -> list[int]:
    """Chunk indexes along one dimension that a strided run touches."""
    if step == 1 or step < chunk:
        return list(range(first // chunk, last // chunk + 1))
    return sorted({i // chunk for i in range(first, last + 1, step)})


def cost(dataset: h5py.Dataset, sel: Selection) -> dict[str, Any]:
    """What reading ``sel`` moves: chunks touched and their stored bytes, from the index."""
    itemsize = dataset.dtype.itemsize
    raw_bytes = sel.size * itemsize
    layout = dataset.id.get_create_plist().get_layout()
    base: dict[str, Any] = {
        "selection_values": sel.size,
        "selection_bytes": raw_bytes,
        "dtype": str(dataset.dtype),
    }
    if layout != h5py.h5d.CHUNKED:
        kind = "contiguous" if layout == h5py.h5d.CONTIGUOUS else "compact"
        first = np.ravel_multi_index(sel.start, dataset.shape) if sel.size else 0
        last = np.ravel_multi_index(sel.last(), dataset.shape) if sel.size else 0
        span = (int(last) - int(first) + 1) * itemsize
        return {**base, "layout": kind, "chunks_touched": 0, "stored_bytes": span, "exact": True}
    chunks = dataset.chunks
    per_dim = [
        _touched(a, b, m, c)
        for a, b, m, c in zip(sel.start, sel.last(), sel.step, chunks, strict=True)
    ]
    n_touched = math.prod(len(d) for d in per_dim)
    dsid = dataset.id
    exact = n_touched <= EXACT_CHUNK_LIMIT
    combos = itertools.product(*per_dim)
    if not exact:
        combos = itertools.islice(combos, 0, None, max(1, n_touched // 2000))
    seen = stored = missing = 0
    for idx in combos:
        offset = tuple(i * c for i, c in zip(idx, chunks, strict=True))
        try:
            info = dsid.get_chunk_info_by_coord(offset)
        except (KeyError, ValueError, RuntimeError):
            info = None
        seen += 1
        if info is None or info.byte_offset is None:
            missing += 1
            continue
        stored += int(info.size)
    if not exact and seen:
        stored = int(stored * n_touched / seen)
        missing = int(missing * n_touched / seen)
    chunk_bytes = math.prod(chunks) * itemsize
    filters = _filters(dataset)
    return {
        **base,
        "layout": "chunked",
        "chunk_shape": list(chunks),
        "chunk_bytes": chunk_bytes,
        "chunks_touched": n_touched,
        "chunks_unwritten": missing,
        "stored_bytes": stored,
        "decoded_bytes": n_touched * chunk_bytes,
        "filters": filters,
        "exact": exact,
    }


def _filters(dataset: h5py.Dataset) -> list[str]:
    out = []
    if dataset.compression:
        opts = dataset.compression_opts
        out.append(f"{dataset.compression}" + (f"({opts})" if opts is not None else ""))
    if dataset.shuffle:
        out.append("shuffle")
    if dataset.fletcher32:
        out.append("fletcher32")
    if dataset.scaleoffset is not None:
        out.append(f"scaleoffset({dataset.scaleoffset})")
    return out


def read(dataset: h5py.Dataset, sel: Selection, decode: bool = True) -> np.ndarray:
    """The selected values; with ``decode``, CF packing applied and fill values as NaN."""
    data = dataset[sel.slices()] if sel.start else dataset[()]
    data = np.asarray(data)
    if not decode or data.dtype.kind not in "iuf":
        return data
    from hdf5_ptc.cf import decode as cf_decode  # noqa: PLC0415

    return cf_decode(dataset, data)
