"""Shared, read-only helpers for the onboard-dataset scripts.

Every helper here only reads input data. Output is written solely to paths the
caller names explicitly (``--out``), never next to or over an input file.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

TABLE_SUFFIXES = frozenset({".parquet", ".pq", ".csv", ".tsv"})


def configure_stdout() -> None:
    """Force UTF-8 console output so Windows code pages never crash a report."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    """Return the hex SHA-256 of one file, streamed."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def read_table(
    path: Path, *, sample: int = 0, columns: list[str] | None = None
) -> pa.Table:
    """Read a Parquet, CSV, or TSV table (optionally only the first ``sample`` rows).

    CSV cells are read with pyarrow's inference; empty cells in string columns
    stay empty strings so an "empty but string-typed" column remains visible.
    """

    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        parquet = pq.ParquetFile(path)
        if sample <= 0:
            return parquet.read(columns=columns)
        batches: list[pa.RecordBatch] = []
        remaining = sample
        for batch in parquet.iter_batches(
            batch_size=min(sample, 65536), columns=columns
        ):
            batches.append(batch.slice(0, remaining))
            remaining -= min(remaining, batch.num_rows)
            if remaining <= 0:
                break
        if not batches:
            return parquet.schema_arrow.empty_table()
        return pa.Table.from_batches(batches)
    if suffix in {".csv", ".tsv"}:
        parse = pacsv.ParseOptions(delimiter="\t" if suffix == ".tsv" else ",")
        convert = pacsv.ConvertOptions(include_columns=columns) if columns else None
        if sample <= 0:
            return pacsv.read_csv(path, parse_options=parse, convert_options=convert)
        reader = pacsv.open_csv(path, parse_options=parse, convert_options=convert)
        batches = []
        remaining = sample
        for batch in reader:
            batches.append(batch.slice(0, remaining))
            remaining -= min(remaining, batch.num_rows)
            if remaining <= 0:
                break
        if not batches:
            return reader.schema.empty_table()
        return pa.Table.from_batches(batches)
    raise ValueError(f"unsupported table type: {path.name} (use Parquet, CSV, or TSV)")


def write_json(payload: Any, out: Path | None) -> None:
    """Write the full JSON report to ``out`` (creating parents) or to stdout."""

    text = json.dumps(payload, indent=2, sort_keys=False, default=str, allow_nan=False)
    if out is None:
        print("--- json ---")
        print(text)
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(f"full report: {out}")


def jsonable(value: Any) -> Any:
    """Convert a scalar into strict JSON (non-finite floats become strings)."""

    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if value in (float("inf"), float("-inf")):
            return "Infinity" if value > 0 else "-Infinity"
        return value
    if isinstance(value, (bytes, bytearray)):
        return f"<{len(value)} bytes>"
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if value is None or isinstance(value, (bool, int, str)):
        return value
    return str(value)
