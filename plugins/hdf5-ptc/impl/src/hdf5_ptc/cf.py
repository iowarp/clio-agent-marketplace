"""What a dataset's attributes mean: CF packing and fill values, and its dimensions.

NetCDF-4 files are HDF5 files whose variables name their dimensions through dimension
scales. ``dimensions`` recovers each axis's name and coordinate variable, so a location
can be reported in latitude and longitude rather than array indexes.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Any

import h5py
import numpy as np

#: Attributes that change what the stored numbers mean.
MEANING_ATTRS = (
    "long_name",
    "standard_name",
    "units",
    "scale_factor",
    "add_offset",
    "_FillValue",
    "missing_value",
    "valid_min",
    "valid_max",
    "valid_range",
    "axis",
    "positive",
    "calendar",
)
MAX_ATTR_CHARS = 200
MAX_ATTR_ITEMS = 8


def plain(value: Any) -> Any:
    """An attribute value as JSON-safe Python, arrays shortened."""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")[:MAX_ATTR_CHARS]
    if isinstance(value, str):
        return value[:MAX_ATTR_CHARS]
    if isinstance(value, np.ndarray):
        if value.dtype.kind in "SO" or value.dtype.kind == "U":
            items = [plain(v) for v in value.ravel()[:MAX_ATTR_ITEMS]]
        elif value.dtype.kind == "V" or value.dtype.names:
            return f"<{value.dtype} x{value.size}>"
        else:
            items = value.ravel()[:MAX_ATTR_ITEMS].tolist()
        if value.size == 1:
            return items[0] if items else None
        return items if value.size <= MAX_ATTR_ITEMS else [*items, f"... {value.size} items"]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, h5py.Reference):
        return "<reference>"
    return value


def attributes(obj: h5py.HLObject, limit: int = 40) -> dict[str, Any]:
    """Up to ``limit`` attributes, skipping the netCDF library's bookkeeping ones."""
    out: dict[str, Any] = {}
    for name in list(obj.attrs)[: limit * 2]:
        if name in ("DIMENSION_LIST", "REFERENCE_LIST", "CLASS", "NAME", "_Netcdf4Dimid"):
            continue
        if name.startswith("_Netcdf4"):
            continue
        try:
            out[name] = plain(obj.attrs[name])
        except (OSError, TypeError, ValueError):
            out[name] = "<unreadable>"
        if len(out) >= limit:
            break
    return out


def meaning(dataset: h5py.Dataset) -> dict[str, Any]:
    """The attributes that change how a dataset's numbers are read."""
    found = {}
    for name in MEANING_ATTRS:
        if name in dataset.attrs:
            found[name] = plain(dataset.attrs[name])
    return found


def _scalar(dataset: h5py.Dataset, name: str) -> float | None:
    if name not in dataset.attrs:
        return None
    value = np.asarray(dataset.attrs[name]).ravel()
    return float(value[0]) if value.size and value.dtype.kind in "iuf" else None


def decode(dataset: h5py.Dataset, data: np.ndarray) -> np.ndarray:
    """Apply ``_FillValue``/``missing_value`` (as NaN) and ``scale_factor``/``add_offset``."""
    fills = [
        v
        for v in (_scalar(dataset, "_FillValue"), _scalar(dataset, "missing_value"))
        if v is not None
    ]
    scale = _scalar(dataset, "scale_factor")
    offset = _scalar(dataset, "add_offset")
    if not fills and scale is None and offset is None:
        return data
    out = data.astype(np.float64 if data.dtype.itemsize > 4 else np.float32, copy=True)
    if fills:
        mask = np.zeros(out.shape, dtype=bool)
        for fill in fills:
            mask |= data == np.asarray(fill, dtype=data.dtype)
        out[mask] = np.nan
    if scale is not None:
        out *= scale
    if offset is not None:
        out += offset
    return out


def dimensions(dataset: h5py.Dataset) -> list[dict[str, Any]]:
    """Each axis: its name, length and the path of its coordinate variable, when known."""
    dims = []
    for axis, length in enumerate(dataset.shape):
        entry: dict[str, Any] = {"axis": axis, "length": int(length)}
        try:
            scales = list(dataset.dims[axis].values())
        except (RuntimeError, TypeError, ValueError):
            scales = []
        if scales:
            scale = scales[0]
            entry["name"] = scale.name.rsplit("/", 1)[-1]
            entry["coordinate"] = scale.name
            if "units" in scale.attrs:
                entry["units"] = plain(scale.attrs["units"])
        else:
            label = dataset.dims[axis].label
            if label:
                entry["name"] = label
        dims.append(entry)
    return dims


_TIME_UNITS = re.compile(
    r"^\s*(seconds?|minutes?|hours?|days?)\s+since\s+(\d{4}-\d{1,2}-\d{1,2})"
    r"(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?",
    re.IGNORECASE,
)
_SECONDS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


def time_text(value: Any, units: Any) -> str | None:
    """An ISO 8601 UTC time for a CF ``<unit> since <date>`` value (Gregorian), else None."""
    match = _TIME_UNITS.match(str(units or ""))
    if match is None or not isinstance(value, (int, float)):
        return None
    unit, date, hh, mm, ss = match.groups()
    y, m, d = (int(p) for p in date.split("-"))
    epoch = dt.datetime(y, m, d, int(hh or 0), int(mm or 0), int(ss or 0), tzinfo=dt.UTC)
    seconds = float(value) * _SECONDS[unit.lower().rstrip("s")]
    try:
        return (epoch + dt.timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")
    except OverflowError:
        return None


def coordinate_values(dataset: h5py.Dataset, index: tuple[int, ...]) -> dict[str, Any]:
    """The coordinate value of each axis at ``index``; CF times as ISO 8601 UTC strings."""
    out: dict[str, Any] = {}
    for dim in dimensions(dataset):
        axis = dim["axis"]
        name = dim.get("name") or f"dim{axis}"
        path = dim.get("coordinate")
        if path and path in dataset.file and dataset.file[path].ndim == 1:
            coord = dataset.file[path]
            if coord.shape[0] == dataset.shape[axis]:
                value = plain(coord[index[axis]])
                when = time_text(value, coord.attrs.get("units"))
                out[name] = when or value
                continue
        out[name] = int(index[axis])
    return out
