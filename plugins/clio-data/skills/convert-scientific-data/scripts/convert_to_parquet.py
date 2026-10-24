# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.24", "pyarrow>=15", "h5py>=3.8"]
# ///
"""Convert HDF5 datasets or ADIOS2 variables to one Parquet file, then verify it.

Every source field gets a recorded decision (copied, widened, decoded, split,
mapped, or skipped with a reason); nothing lossy happens without an explicit
option. After writing, the file is read back and compared column by column:
row count, schema, null and NaN counts, and a SHA-256 over each column's
logical values. The report (JSON) and the Parquet key-value metadata carry the
decisions and the checks.

HDF5 (rows are the first axis; every selected dataset must have the same
length)::

    uv run --no-project SCRIPT hdf5 SOURCE.h5 --datasets /grp/a /grp/b -o OUT.parquet
    uv run --no-project SCRIPT hdf5 SOURCE.h5 --group /grp -o OUT.parquet

ADIOS2 BP4/BP5 (rows are steps for global values, or the concatenated elements
of one-dimensional global arrays with a ``step`` column)::

    uv run --no-project --with adios2 SCRIPT adios RUN.bp --variables T P -o OUT.parquet

Options that change values, all off by default: ``--complex split``,
``--cf-time decode``, ``--mask-fill``, ``--unpack``. ``--skip NAME`` leaves a
field out on purpose. Exit status: 0 written and verified (skipped fields are
listed), 1 written but a check failed, 2 nothing written (usage, a field that
cannot be converted as asked, or a refusal).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

SCRIPT_VERSION = "1.0.0"
METADATA_KEY = b"clio.conversion"
CF_UNITS = re.compile(
    r"^\s*(?P<unit>days?|hours?|hrs?|minutes?|mins?|seconds?|secs?|s|milliseconds?|ms|"
    r"microseconds?|us)\s+since\s+(?P<epoch>.+?)\s*$",
    re.IGNORECASE,
)
UNIT_US = {
    "day": 86_400_000_000,
    "hour": 3_600_000_000,
    "hr": 3_600_000_000,
    "minute": 60_000_000,
    "min": 60_000_000,
    "second": 1_000_000,
    "sec": 1_000_000,
    "s": 1_000_000,
    "millisecond": 1_000,
    "ms": 1_000,
    "microsecond": 1,
    "us": 1,
}
STANDARD_CALENDARS = {"standard", "gregorian", "proleptic_gregorian"}


class ConversionError(Exception):
    """A field cannot be converted as asked; nothing is written."""


@dataclass
class Options:
    complex_mode: str = "refuse"  # refuse | split
    cf_time: str = "keep"  # keep | decode
    mask_fill: bool = False
    unpack: bool = False
    skip: frozenset[str] = frozenset()


@dataclass
class Column:
    """One output column and the decision that produced it."""

    name: str
    source: str
    source_dtype: str
    action: str
    arrow_type: pa.DataType | None
    convert: Callable[[np.ndarray], pa.Array] | None
    lossless: bool = True
    notes: list[str] = field(default_factory=list)
    attrs: dict[str, Any] = field(default_factory=dict)
    # Value-preserving actions are checksummed from the raw source values;
    # transforming ones from the converted values (stated in the report).
    source_comparable: bool = True
    fill_values: list[Any] = field(default_factory=list)
    masked: int = 0


# ----------------------------------------------------------------- hashing


class ColumnHash:
    """SHA-256 over a column's logical values, independent of batching and storage type.

    Integers hash as int64 (uint64 as uint64), floats as float64 with one NaN
    pattern, booleans as bytes, everything else as canonical JSON per element.
    Nulls are hashed separately as positions, so a null and a sentinel differ.
    """

    def __init__(self) -> None:
        self.values = hashlib.sha256()
        self.nulls = hashlib.sha256()
        self.position = 0

    def update(self, array: pa.Array | pa.ChunkedArray) -> None:
        if isinstance(array, pa.ChunkedArray):
            for chunk in array.chunks:
                self.update(chunk)
            return
        if pa.types.is_dictionary(array.type):
            array = array.dictionary_decode()
        valid = np.asarray(array.is_valid().to_numpy(zero_copy_only=False), dtype=bool)
        for index in np.flatnonzero(~valid):
            self.nulls.update(int(self.position + index).to_bytes(8, "little"))
        self.position += len(array)
        kind = array.type
        if pa.types.is_integer(kind) or pa.types.is_floating(kind) or pa.types.is_boolean(kind):
            filled = array.fill_null(False if pa.types.is_boolean(kind) else 0)
            values = filled.to_numpy(zero_copy_only=False)
            self.values.update(canonical_numeric(values).tobytes())
            return
        if pa.types.is_timestamp(kind):
            values = array.cast(pa.int64()).fill_null(0).to_numpy(zero_copy_only=False)
            self.values.update(values.astype("<i8").tobytes())
            return
        for item in array.to_pylist():
            self.values.update(canonical_json(item).encode("utf-8") + b"\x1e")

    def update_numpy(self, values: np.ndarray, mask: np.ndarray | None = None) -> None:
        """Hash raw source values (one-dimensional numeric or bool), nulls given by mask."""

        if mask is not None:
            for index in np.flatnonzero(mask):
                self.nulls.update(int(self.position + index).to_bytes(8, "little"))
            values = np.where(mask, np.zeros(1, values.dtype), values)
        self.position += len(values)
        self.values.update(canonical_numeric(values).tobytes())

    def hexdigest(self) -> str:
        combined = hashlib.sha256(self.values.digest() + self.nulls.digest())
        return combined.hexdigest()


def canonical_numeric(values: np.ndarray) -> np.ndarray:
    kind = values.dtype.kind
    if kind == "b":
        return values.astype("u1")
    if kind == "u" and values.dtype.itemsize == 8:
        return values.astype("<u8")
    if kind in "iu":
        return values.astype("<i8")
    if kind == "f":
        wide = values.astype("<f8")
        return np.where(np.isnan(wide), np.float64("nan"), wide)
    raise TypeError(f"not numeric: {values.dtype}")


def canonical_json(item: Any) -> str:
    def norm(value: Any) -> Any:
        if isinstance(value, float):
            return "nan" if math.isnan(value) else float.hex(value)
        if isinstance(value, bytes):
            return {"bytes": value.hex()}
        if isinstance(value, dict):
            return {k: norm(v) for k, v in value.items()}
        if isinstance(value, list | tuple):
            return [norm(v) for v in value]
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    return json.dumps(norm(item), sort_keys=True, separators=(",", ":"))


# ------------------------------------------------------------ dtype policy


def h5py_module() -> Any:
    import h5py  # noqa: PLC0415

    return h5py


def plain(value: Any) -> Any:
    """An attribute value as JSON-friendly data."""

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, np.ndarray):
        return [plain(v) for v in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, list | tuple):
        return [plain(v) for v in value]
    return value


def field_policy(
    name: str, dtype: np.dtype, opts: Options, attrs: dict[str, Any]
) -> tuple[pa.DataType | None, Callable[[np.ndarray], pa.Array] | None, str, bool, list[str]]:
    """Decide how one source dtype maps to Arrow.

    Returns (arrow type, converter, action, lossless, notes); a None converter
    means the field is skipped and the notes say why.
    """

    h5py = h5py_module()
    if dtype.subdtype is not None:  # a fixed-size array inside each element
        base, shape = dtype.subdtype
        size = int(np.prod(shape))
        child_type, child, action, lossless, notes = field_policy(name, base, opts, {})
        if child is None:
            return None, None, "skip", False, [f"array of {base}: {'; '.join(notes)}"]

        def convert_sub(values: np.ndarray) -> pa.Array:
            flat = child(np.ascontiguousarray(values).reshape(-1))
            return pa.FixedSizeListArray.from_arrays(flat, size)

        note = f"fixed-size list of {size} ({action} per element), element shape {list(shape)}"
        return pa.list_(child_type, size), convert_sub, "array", lossless, [note, *notes]
    if dtype.names:  # compound: one struct field per member
        children = []
        notes: list[str] = []
        lossless = True
        for member in dtype.names:
            if f"{name}.{member}" in opts.skip:
                notes.append(f"member {member}: skipped on request")
                lossless = False
                continue
            ctype, conv, action, ok, sub = field_policy(
                f"{name}.{member}", dtype.fields[member][0], opts, {}
            )
            if conv is None:
                notes.append(f"member {member}: skipped ({'; '.join(sub)})")
                lossless = False
                continue
            children.append((member, ctype, conv))
            notes.extend(f"member {member}: {s}" for s in sub)
        if not children:
            return None, None, "skip", False, ["compound with no convertible member", *notes]

        def convert_struct(values: np.ndarray) -> pa.Array:
            arrays = [conv(np.ascontiguousarray(values[member])) for member, _, conv in children]
            return pa.StructArray.from_arrays(arrays, [m for m, _, _ in children])

        struct = pa.struct([(m, t) for m, t, _ in children])
        return struct, convert_struct, "struct", lossless, notes
    if h5py.check_ref_dtype(dtype) is not None:
        return None, None, "skip", False, [
            "HDF5 object or region references point inside the source file and have no "
            "Parquet meaning; record the referenced paths separately if they matter"
        ]
    enum = h5py.check_enum_dtype(dtype)
    if enum is not None:
        ordered = sorted(enum.items(), key=lambda kv: kv[1])
        labels = [k for k, _ in ordered]
        codes = np.array([v for _, v in ordered])

        def convert_enum(values: np.ndarray) -> pa.Array:
            index = np.searchsorted(codes, values)
            bad = (index >= len(codes)) | (codes[np.minimum(index, len(codes) - 1)] != values)
            if bad.any():
                raise ConversionError(
                    f"{name}: enum value(s) {sorted(set(values[bad].tolist()))[:5]} "
                    "are not in the declared mapping"
                )
            return pa.DictionaryArray.from_arrays(
                pa.array(index.astype("int32")), pa.array(labels, pa.string())
            )

        return (
            pa.dictionary(pa.int32(), pa.string()),
            convert_enum,
            "enum->dictionary",
            True,
            [f"labels {labels} (codes {codes.tolist()})"],
        )
    string = h5py.check_string_dtype(dtype)
    if string is not None:
        encoding = string.encoding

        def convert_str(values: np.ndarray) -> pa.Array:
            out = []
            for item in values.reshape(-1).tolist():
                if isinstance(item, bytes):
                    try:
                        item = item.decode(encoding)
                    except UnicodeDecodeError as exc:
                        raise ConversionError(
                            f"{name}: bytes that are not valid {encoding} ({exc.reason}); "
                            f"--skip {name} or convert it as binary in your own script"
                        ) from exc
                out.append(item)
            return pa.array(out, pa.string())

        kind = "variable-length" if string.length is None else f"fixed-length {string.length}"
        return pa.string(), convert_str, "decode", True, [f"{kind} {encoding} string"]
    vlen = h5py.check_vlen_dtype(dtype)
    if vlen is not None:
        base = np.dtype(vlen)
        ctype, conv, action, ok, sub = field_policy(name, base, opts, {})
        if conv is None:
            return None, None, "skip", False, [f"variable-length sequence of {base}: {sub}"]

        def convert_vlen(values: np.ndarray) -> pa.Array:
            offsets = [0]
            parts = []
            for item in values.reshape(-1):
                part = np.asarray(item, dtype=base)
                parts.append(part)
                offsets.append(offsets[-1] + len(part))
            flat = conv(np.concatenate(parts) if parts else np.empty(0, base))
            return pa.ListArray.from_arrays(pa.array(offsets, pa.int32()), flat)

        return pa.list_(ctype), convert_vlen, "list", ok, [f"variable-length {base}", *sub]
    kind = dtype.kind
    if kind == "b":
        return pa.bool_(), lambda v: pa.array(v.reshape(-1), pa.bool_()), "copy", True, []
    if kind in "iu":
        arrow = pa.from_numpy_dtype(dtype)
        notes = []
        if kind == "u" and dtype.itemsize == 8:
            notes.append(
                "uint64 is stored as INT64 with an unsigned annotation; readers that ignore it "
                "show values above 2^63-1 as negative"
            )
        return arrow, lambda v: pa.array(v.reshape(-1), arrow), "copy", True, notes
    if kind == "f":
        if dtype.itemsize == 2:
            return (
                pa.float32(),
                lambda v: pa.array(v.reshape(-1).astype("float32"), pa.float32()),
                "widen",
                True,
                ["float16 widened to float32 (exact)"],
            )
        if dtype.itemsize in (4, 8):
            arrow = pa.from_numpy_dtype(dtype)
            return arrow, lambda v: pa.array(v.reshape(-1), arrow), "copy", True, []
        return None, None, "skip", False, [f"{dtype} has no Parquet float type"]
    if kind == "c":
        if opts.complex_mode != "split":
            return None, None, "skip", False, [
                f"{dtype}: complex values have no Parquet type; rerun with --complex split "
                "for a struct of real and imag, or keep them out"
            ]
        part = np.dtype(f"f{dtype.itemsize // 2}")
        ptype = pa.from_numpy_dtype(part)

        def convert_complex(values: np.ndarray) -> pa.Array:
            flat = values.reshape(-1)
            return pa.StructArray.from_arrays(
                [pa.array(flat.real.astype(part), ptype), pa.array(flat.imag.astype(part), ptype)],
                ["real", "imag"],
            )

        return (
            pa.struct([("real", ptype), ("imag", ptype)]),
            convert_complex,
            "complex->struct",
            True,
            ["complex split into a struct of real and imag"],
        )
    return None, None, "skip", False, [f"{dtype} (kind {kind!r}) has no mapping"]


def cf_time_policy(name: str, attrs: dict[str, Any]) -> tuple[int, int] | None:
    """(epoch in microseconds, microseconds per unit) for a decodable CF time column."""

    units = attrs.get("units")
    if not isinstance(units, str):
        return None
    match = CF_UNITS.match(units)
    if match is None:
        return None
    calendar = str(attrs.get("calendar", "standard")).lower()
    if calendar not in STANDARD_CALENDARS:
        raise ConversionError(
            f"{name}: calendar {calendar!r} is not a standard Gregorian calendar; "
            "keep it numeric (--cf-time keep) or decode it with cftime yourself"
        )
    unit = match.group("unit").lower()
    unit = unit[:-1] if unit.endswith("s") and unit not in ("s", "ms", "us") else unit
    epoch_text = match.group("epoch").replace("UTC", "").strip()
    epoch_text = re.sub(r"\s+", " ", epoch_text)
    epoch = None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        stamp = epoch_text.rstrip("Z").strip()
        offset = re.search(r"\s*([+-])(\d{1,2}):?(\d{2})?$", stamp) if fmt != "%Y-%m-%d" else None
        shift = timedelta(0)
        if offset and stamp.count("-") > 2:
            sign = 1 if offset.group(1) == "+" else -1
            shift = sign * timedelta(hours=int(offset.group(2)), minutes=int(offset.group(3) or 0))
            stamp = stamp[: offset.start()]
        try:
            epoch = datetime.strptime(stamp, fmt).replace(tzinfo=timezone.utc) - shift
            break
        except ValueError:
            continue
    if epoch is None:
        raise ConversionError(f"{name}: cannot parse the CF epoch in {units!r}")
    epoch_us = int((epoch - datetime(1970, 1, 1, tzinfo=timezone.utc)) / timedelta(microseconds=1))
    return epoch_us, UNIT_US[unit]


def wrap_value_options(col: Column, opts: Options) -> None:
    """Apply --mask-fill, --unpack and --cf-time decode around a numeric column."""

    base = col.convert
    attrs = col.attrs
    fills = [v for key in ("_FillValue", "missing_value") for v in np.atleast_1d(attrs.get(key, []))]
    col.fill_values = [plain(v) for v in fills]
    scale, offset = attrs.get("scale_factor"), attrs.get("add_offset")
    if col.fill_values:
        col.notes.append(
            f"declares fill/missing values {col.fill_values}"
            + ("; masked to null (--mask-fill)" if opts.mask_fill else "; kept as values")
        )
    if scale is not None or offset is not None:
        col.notes.append(
            f"packed (scale_factor={plain(scale)}, add_offset={plain(offset)})"
            + ("; unpacked to float64 (--unpack)" if opts.unpack else "; kept packed")
        )
    time = cf_time_policy(col.name, attrs) if opts.cf_time == "decode" else None
    if opts.cf_time == "keep" and isinstance(attrs.get("units"), str) and CF_UNITS.match(attrs["units"]):
        col.notes.append(f"CF time ({attrs['units']}) kept numeric; --cf-time decode converts it")
    mask_fill = opts.mask_fill and bool(fills)
    unpack = opts.unpack and (scale is not None or offset is not None)
    if not (mask_fill or unpack or time):
        return
    col.source_comparable = False
    if unpack or time:
        col.lossless = False

    def convert(values: np.ndarray) -> pa.Array:
        flat = values.reshape(-1)
        mask = np.zeros(len(flat), bool)
        if mask_fill:
            for fill in fills:
                mask |= (flat == fill) | (np.isnan(flat) & np.isnan(fill) if flat.dtype.kind == "f" else False)
            col.masked += int(mask.sum())
        data: np.ndarray = flat
        if unpack:
            data = flat.astype("float64") * float(1 if scale is None else scale) + float(
                0 if offset is None else offset
            )
        if time:
            epoch_us, per_unit = time
            stamp = np.rint(data.astype("float64") * per_unit) + epoch_us
            return pa.array(stamp.astype("int64"), pa.timestamp("us", tz="UTC"), mask=mask)
        if not (mask_fill or unpack):
            return base(values)
        arrow = pa.float64() if unpack else col.arrow_type
        return pa.array(data, arrow, mask=mask)

    if time:
        col.arrow_type = pa.timestamp("us", tz="UTC")
        col.action = "cf-time->timestamp"
        col.notes.append("decoded to timestamp[us, UTC], rounded to the microsecond")
    elif unpack:
        col.arrow_type = pa.float64()
        col.action = "unpack"
    else:
        col.action = f"{col.action}+mask"
    col.convert = convert


def make_column(name: str, source: str, dtype: np.dtype, attrs: dict[str, Any], opts: Options) -> Column:
    arrow, convert, action, lossless, notes = field_policy(name, dtype, opts, attrs)
    col = Column(
        name=name,
        source=source,
        source_dtype=str(dtype),
        action=action,
        arrow_type=arrow,
        convert=convert,
        lossless=lossless,
        notes=list(notes),
        attrs=attrs,
    )
    if convert is not None and dtype.kind in "iuf" and dtype.subdtype is None and not dtype.names:
        wrap_value_options(col, opts)
    if action not in ("copy", "widen", "decode"):
        col.source_comparable = False
    return col


# ------------------------------------------------------------------ sources


@dataclass
class Plan:
    columns: list[Column]
    skipped: list[dict[str, Any]]
    rows: int
    batches: Callable[[int], Iterator[dict[str, np.ndarray]]]
    file_metadata: dict[str, Any]
    extra_columns: list[tuple[str, pa.DataType]] = field(default_factory=list)


def unique_names(paths: list[str]) -> dict[str, str]:
    base = {p: p.rstrip("/").rsplit("/", 1)[-1] for p in paths}
    counts: dict[str, int] = {}
    for name in base.values():
        counts[name] = counts.get(name, 0) + 1
    return {p: (n if counts[n] == 1 else p.strip("/").replace("/", ".")) for p, n in base.items()}


def plan_hdf5(source: Path, datasets: list[str], group: str | None, opts: Options) -> Plan:
    h5py = h5py_module()
    handle = h5py.File(source, "r")
    if group is not None:
        node = handle[group]
        if not isinstance(node, h5py.Group):
            raise ConversionError(f"{group} is not a group")
        datasets = [
            f"{node.name.rstrip('/')}/{key}"
            for key in node
            if isinstance(node.get(key, getlink=False), h5py.Dataset)
        ]
    if not datasets:
        raise ConversionError("no datasets selected")
    names = unique_names(datasets)
    columns: list[Column] = []
    skipped: list[dict[str, Any]] = []
    file_meta: dict[str, Any] = {"attributes": {k: plain(v) for k, v in handle.attrs.items()}}
    lengths: dict[str, int] = {}
    readers: list[tuple[Any, list[tuple[Column, str | None]]]] = []
    for path in datasets:
        dset = handle[path]
        if not isinstance(dset, h5py.Dataset):
            raise ConversionError(f"{path} is not a dataset")
        attrs = {k: plain(v) if k not in ("_FillValue", "missing_value", "scale_factor", "add_offset") else v for k, v in dset.attrs.items()}
        name = names[path]
        if name in opts.skip or path in opts.skip:
            skipped.append({"source": path, "dtype": str(dset.dtype), "reason": "skipped on request"})
            continue
        if dset.shape == ():
            file_meta.setdefault("scalars", {})[path] = plain(dset[()])
            skipped.append({"source": path, "dtype": str(dset.dtype), "reason": "scalar; value kept in the file metadata"})
            continue
        lengths[path] = dset.shape[0]
        element = dset.dtype if len(dset.shape) == 1 else np.dtype((dset.dtype, dset.shape[1:]))
        if dset.dtype.names and len(dset.shape) == 1:
            made = []
            for member in dset.dtype.names:
                cname = member if len(datasets) == 1 else f"{name}.{member}"
                if cname in opts.skip or f"{path}.{member}" in opts.skip:
                    skipped.append({"source": f"{path}.{member}", "dtype": str(dset.dtype.fields[member][0]), "reason": "skipped on request"})
                    continue
                col = make_column(cname, f"{path}.{member}", dset.dtype.fields[member][0], {}, opts)
                if col.convert is None:
                    skipped.append({"source": col.source, "dtype": col.source_dtype, "reason": "; ".join(col.notes)})
                    continue
                made.append((col, member))
            readers.append((dset, made))
            columns.extend(col for col, _ in made)
            continue
        col = make_column(name, path, element, attrs, opts)
        if len(dset.shape) > 1:
            col.notes.insert(0, f"{len(dset.shape)}-D dataset: one row per first-axis index")
        if col.convert is None:
            skipped.append({"source": path, "dtype": str(dset.dtype), "reason": "; ".join(col.notes)})
            continue
        readers.append((dset, [(col, None)]))
        columns.append(col)
    if len(set(lengths.values())) > 1:
        raise ConversionError(
            "selected datasets have different first-axis lengths: "
            + ", ".join(f"{p}={n}" for p, n in lengths.items())
            + "; convert them to separate files or select equal-length datasets"
        )
    rows = next(iter(lengths.values()), 0)

    def batches(size: int) -> Iterator[dict[str, np.ndarray]]:
        for start in range(0, rows, size):
            stop = min(rows, start + size)
            batch: dict[str, np.ndarray] = {}
            for dset, cols in readers:
                values = dset[start:stop]
                for col, member in cols:
                    batch[col.name] = values if member is None else np.ascontiguousarray(values[member])
            yield batch

    return Plan(columns, skipped, rows, batches, file_meta)


ADIOS_TYPES = {
    "int8_t": "i1", "int16_t": "i2", "int32_t": "i4", "int64_t": "i8",
    "uint8_t": "u1", "uint16_t": "u2", "uint32_t": "u4", "uint64_t": "u8",
    "float": "f4", "double": "f8", "float complex": "c8", "double complex": "c16",
}


def adios_attribute(reader: Any, key: str, meta: dict[str, str]) -> Any:
    """An ADIOS2 attribute's value (strings through read_attribute_string)."""

    if meta.get("Type") == "string":
        values = list(reader.read_attribute_string(key))
        return values[0] if len(values) == 1 else values
    value = plain(reader.read_attribute(key))
    return value[0] if isinstance(value, list) and len(value) == 1 else value


def plan_adios(source: Path, variables: list[str], steps: str, opts: Options) -> Plan:
    try:
        import adios2  # noqa: PLC0415
    except ImportError as exc:
        raise ConversionError("adios2 is not installed: rerun with `uv run --with adios2 ...`") from exc
    if not hasattr(adios2, "FileReader"):
        raise ConversionError(f"adios2 {adios2.__version__} has no FileReader; use adios2 2.10 or later")
    reader = adios2.FileReader(str(source))
    available = reader.available_variables()
    attributes = reader.available_attributes()
    total = reader.num_steps()
    first, _, last = steps.partition(":") if steps != "all" else ("0", ":", str(total))
    step_list = list(range(int(first or 0), min(total, int(last or total))))
    if not step_list:
        raise ConversionError(f"no steps selected (file has {total})")
    columns: list[Column] = []
    skipped: list[dict[str, Any]] = []
    shapes: dict[str, str] = {}
    for name in variables:
        if name not in available:
            raise ConversionError(f"{name}: not a variable (have {sorted(available)[:20]})")
        info = available[name]
        if name in opts.skip:
            skipped.append({"source": name, "dtype": info["Type"], "reason": "skipped on request"})
            continue
        kind = info["Type"]
        shape = info.get("Shape", "")
        if kind == "string":
            dtype = np.dtype(object)
        elif kind in ADIOS_TYPES:
            dtype = np.dtype(ADIOS_TYPES[kind])
        else:
            skipped.append({"source": name, "dtype": kind, "reason": f"ADIOS type {kind} has no mapping"})
            continue
        if shape == "" and info.get("SingleValue") != "true":
            raise ConversionError(f"{name}: a local array; read it per block in your own script")
        if shape and "," in shape:
            raise ConversionError(f"{name}: {shape} is not one-dimensional; select a slice in your own script")
        shapes[name] = "value" if shape == "" else "array"
        prefix = f"{name}/"
        attrs = {k[len(prefix):]: adios_attribute(reader, k, v) for k, v in attributes.items() if k.startswith(prefix)}
        if kind == "string":
            col = Column(name, name, kind, "copy", pa.string(), lambda v: pa.array([str(x) for x in v.reshape(-1)], pa.string()), attrs=attrs)
        else:
            col = make_column(name, name, dtype, attrs, opts)
        if col.convert is None:
            skipped.append({"source": name, "dtype": kind, "reason": "; ".join(col.notes)})
            continue
        columns.append(col)
    if len(set(shapes.values())) > 1:
        raise ConversionError("mixing global values and arrays; convert them to separate files")
    per_step = "value" if set(shapes.values()) == {"value"} else "array"

    def read(name: str, step: int) -> np.ndarray:
        value = reader.read(name, step_selection=[step, 1])
        return np.atleast_1d(np.asarray(value))

    rows = 0
    if per_step == "array":
        for step in step_list:
            lengths = {c.name: len(read(c.name, step)) for c in columns}
            if len(set(lengths.values())) > 1:
                raise ConversionError(f"step {step}: arrays of different lengths {lengths}")
            rows += next(iter(lengths.values()), 0)
    else:
        rows = len(step_list)

    def batches(size: int) -> Iterator[dict[str, np.ndarray]]:
        if per_step == "value":
            for start in range(0, len(step_list), size):
                chunk = step_list[start : start + size]
                batch = {c.name: np.concatenate([read(c.name, s) for s in chunk]) for c in columns}
                batch["step"] = np.array(chunk, dtype="int64")
                yield batch
            return
        for step in step_list:
            batch = {c.name: read(c.name, step) for c in columns}
            n = len(next(iter(batch.values()))) if batch else 0
            batch["step"] = np.full(n, step, dtype="int64")
            yield batch

    meta = {
        "attributes": {k: adios_attribute(reader, k, v) for k, v in attributes.items() if "/" not in k},
        "steps": [step_list[0], step_list[-1]],
        "adios2_version": adios2.__version__,
    }
    return Plan(columns, skipped, rows, batches, meta, extra_columns=[("step", pa.int64())])


# ---------------------------------------------------------------- execution


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else [path]
    for item in files:
        if path.is_dir():
            digest.update(item.relative_to(path).as_posix().encode() + b"\0")
        with item.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
    return digest.hexdigest()


def count_nan(array: pa.Array | pa.ChunkedArray) -> int:
    """NaN count over every floating leaf of a column (lists and structs included)."""

    if isinstance(array, pa.ChunkedArray):
        return sum(count_nan(chunk) for chunk in array.chunks)
    kind = array.type
    if pa.types.is_floating(kind):
        return int(np.isnan(array.to_numpy(zero_copy_only=False).astype("float64")).sum())
    if pa.types.is_list(kind) or pa.types.is_large_list(kind) or pa.types.is_fixed_size_list(kind):
        return count_nan(array.flatten())
    if pa.types.is_struct(kind):
        return sum(count_nan(array.field(i)) for i in range(kind.num_fields))
    return 0


def source_numeric(values: np.ndarray) -> np.ndarray | None:
    flat = np.asarray(values).reshape(-1)
    return flat if flat.dtype.kind in "biuf" else None


def run(args: argparse.Namespace) -> int:
    source = Path(args.source).resolve()
    out = Path(args.output).resolve()
    if not source.exists():
        return refuse(f"source not found: {source}")
    if out == source or (source.is_dir() and out.is_relative_to(source)):
        return refuse("the output must not be the source or inside it")
    if out.exists() and not args.overwrite:
        return refuse(f"{out} exists; pass --overwrite to replace it")
    opts = Options(
        complex_mode=args.complex,
        cf_time=args.cf_time,
        mask_fill=args.mask_fill,
        unpack=args.unpack,
        skip=frozenset(args.skip or ()),
    )
    try:
        if args.format == "hdf5":
            plan = plan_hdf5(source, args.datasets or [], args.group, opts)
        else:
            plan = plan_adios(source, args.variables, args.steps, opts)
    except ConversionError as exc:
        return refuse(str(exc))
    if not plan.columns:
        return refuse("no field can be converted: " + json.dumps(plan.skipped))
    fields = []
    for col in plan.columns:
        meta = {"source": col.source, "source_dtype": col.source_dtype, "action": col.action}
        if col.attrs:
            meta["attributes"] = json.dumps(plain(col.attrs), default=str)
        fields.append(pa.field(col.name, col.arrow_type, metadata=meta))
    fields.extend(pa.field(n, t, metadata={"source": "ADIOS2 step index"}) for n, t in plan.extra_columns)
    provenance = {
        "script": "convert_to_parquet.py",
        "version": SCRIPT_VERSION,
        "source": str(source),
        "source_format": args.format,
        "source_sha256": fingerprint(source),
        "options": {
            "complex": args.complex,
            "cf_time": args.cf_time,
            "mask_fill": args.mask_fill,
            "unpack": args.unpack,
            "skip": sorted(opts.skip),
        },
        "columns": [
            {"name": c.name, "source": c.source, "action": c.action, "lossless": c.lossless, "notes": c.notes}
            for c in plan.columns
        ],
        "skipped": plan.skipped,
        "file": plan.file_metadata,
    }
    schema = pa.schema(fields, metadata={METADATA_KEY: json.dumps(provenance, default=str).encode()})
    expected = {c.name: ColumnHash() for c in plan.columns}
    for name, _ in plan.extra_columns:
        expected[name] = ColumnHash()
    nan_source = {c.name: 0 for c in plan.columns}
    written = 0
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".partial")
    try:
        with pq.ParquetWriter(tmp, schema, compression=args.compression) as writer:
            for batch in plan.batches(args.batch_rows):
                arrays = []
                for col in plan.columns:
                    raw = batch[col.name]
                    array = col.convert(raw)
                    arrays.append(array)
                    numeric = source_numeric(raw)
                    if numeric is not None and numeric.dtype.kind == "f":
                        nan_source[col.name] += int(np.isnan(numeric).sum())
                    elif raw.dtype.kind == "c":
                        flat = raw.reshape(-1)
                        nan_source[col.name] += int(np.isnan(flat.real).sum() + np.isnan(flat.imag).sum())
                    else:
                        nan_source[col.name] += count_nan(array)
                    if col.source_comparable and numeric is not None:
                        expected[col.name].update_numpy(numeric)
                    else:
                        expected[col.name].update(array)
                for name, _ in plan.extra_columns:
                    array = pa.array(batch[name], pa.int64())
                    arrays.append(array)
                    expected[name].update(array)
                record = pa.RecordBatch.from_arrays(arrays, schema=schema)
                writer.write_batch(record, row_group_size=args.batch_rows)
                written += record.num_rows
    except ConversionError as exc:
        tmp.unlink(missing_ok=True)
        return refuse(str(exc))
    tmp.replace(out)
    report = verify(out, plan, schema, expected, nan_source, written)
    report["provenance"] = provenance
    report["output"] = str(out)
    text = json.dumps(report, indent=2, default=str)
    if args.report:
        Path(args.report).write_text(text + "\n", encoding="utf-8")
    print(summarize(report))
    return 0 if report["ok"] else 1


def verify(
    out: Path,
    plan: Plan,
    schema: pa.Schema,
    expected: dict[str, ColumnHash],
    nan_source: dict[str, int],
    written: int,
) -> dict[str, Any]:
    handle = pq.ParquetFile(out)
    got = {name: ColumnHash() for name in expected}
    nulls = {name: 0 for name in expected}
    nans = {name: 0 for name in expected}
    for batch in handle.iter_batches(batch_size=65536):
        for name in expected:
            column = batch.column(name)
            got[name].update(column)
            nulls[name] += column.null_count
            nans[name] += count_nan(column)
    checks = []
    rows = handle.metadata.num_rows
    checks.append({"check": "rows", "expected": plan.rows, "written": written, "parquet": rows, "ok": rows == plan.rows == written})
    same_schema = handle.schema_arrow.remove_metadata().equals(schema.remove_metadata(), check_metadata=False)
    checks.append({"check": "schema", "ok": same_schema})
    columns = []
    by_name = {c.name: c for c in plan.columns}
    for name in expected:
        col = by_name.get(name)
        exp_nulls = col.masked if col else 0
        row = {
            "name": name,
            "action": col.action if col else "index",
            "lossless": col.lossless if col else True,
            "checksum_basis": "source values" if (col is None or col.source_comparable) else "converted values",
            "sha256_expected": expected[name].hexdigest(),
            "sha256_parquet": got[name].hexdigest(),
            "nulls": nulls[name],
            "nulls_expected": exp_nulls,
            "masked_to_null": col.masked if col else 0,
            "nan_source": nan_source.get(name, 0),
            "nan_parquet": nans[name],
            "notes": col.notes if col else [],
        }
        row["ok"] = (
            row["sha256_expected"] == row["sha256_parquet"]
            and row["nulls"] == exp_nulls
            and (
                col is None
                or col.action.startswith(("unpack", "cf-time"))
                or col.action.endswith("+mask")  # a NaN fill value becomes null
                or row["nan_source"] == row["nan_parquet"]
            )
        )
        columns.append(row)
    ok = all(c["ok"] for c in checks) and all(c["ok"] for c in columns)
    return {"ok": ok, "rows": rows, "checks": checks, "columns": columns, "skipped": plan.skipped}


def summarize(report: dict[str, Any]) -> str:
    lines = [f"{'OK' if report['ok'] else 'CHECK FAILED'}: {report['rows']} rows -> {report['output']}"]
    for check in report["checks"]:
        lines.append(f"  {check['check']}: {'ok' if check['ok'] else 'MISMATCH ' + json.dumps(check)}")
    for col in report["columns"]:
        flag = "ok" if col["ok"] else "MISMATCH"
        lossy = "" if col["lossless"] else " LOSSY"
        lines.append(
            f"  {col['name']}: {col['action']}{lossy}, nulls {col['nulls']}, NaN {col['nan_parquet']}"
            f" (source {col['nan_source']}), sha256 {col['sha256_parquet'][:16]} [{col['checksum_basis']}] {flag}"
        )
        lines.extend(f"      {note}" for note in col["notes"])
    for item in report["skipped"]:
        lines.append(f"  SKIPPED {item['source']} ({item['dtype']}): {item['reason']}")
    return "\n".join(lines)


def refuse(message: str) -> int:
    print(f"not converted: {message}", file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="format", required=True)
    for name in ("hdf5", "adios"):
        p = sub.add_parser(name)
        p.add_argument("source")
        p.add_argument("-o", "--output", required=True)
        p.add_argument("--report", help="write the JSON report here")
        p.add_argument("--complex", choices=["refuse", "split"], default="refuse")
        p.add_argument("--cf-time", choices=["keep", "decode"], default="keep")
        p.add_argument("--mask-fill", action="store_true", help="_FillValue/missing_value -> null")
        p.add_argument("--unpack", action="store_true", help="apply scale_factor/add_offset")
        p.add_argument("--skip", action="append", help="leave this field out (repeatable)")
        p.add_argument("--compression", default="zstd")
        p.add_argument("--batch-rows", type=int, default=1_000_000)
        p.add_argument("--overwrite", action="store_true")
        if name == "hdf5":
            group = p.add_mutually_exclusive_group(required=True)
            group.add_argument("--datasets", nargs="+")
            group.add_argument("--group")
        else:
            p.add_argument("--variables", nargs="+", required=True)
            p.add_argument("--steps", default="all", help="all, or FIRST:STOP")
    return parser


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
