# /// script
# requires-python = ">=3.11"
# dependencies = ["pyarrow>=15", "jsonschema>=4.18"]
# ///
# pyright: reportAttributeAccessIssue=false
# (pyarrow.compute functions are generated at import time; there are no stubs.)
"""Validate phenotyping views (Parquet/CSV) against the seam JSON Schemas.

The five shapes -- design, observations, spectra, assets, events -- live in
``../schemas/<kind>.schema.json``. Each schema describes ONE ROW; this script
checks a whole table against it:

* every required column is present;
* column storage types are compatible with the schema (a dose stored as text
  where a number is required is an error; timestamps may be Arrow timestamps
  or ISO 8601 strings);
* required, non-nullable columns hold no nulls;
* the ``x-primary-key`` columns are unique (duplicates mean the view mixes
  repeated observations or a join fanned out);
* no numeric column carries a sentinel (|x| >= 1e300) -- missing must be null;
* the first ``--sample`` rows validate against the schema with jsonschema.

The kind is taken from ``--kind`` or from the file name's first word
(``design...``, ``observations...``). Inputs are only read.

Usage::

    python validate_views.py VIEW [VIEW ...] [--kind KIND] [--sample 2000] [--out report.json]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import jsonschema
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"
KINDS = ("design", "observations", "spectra", "assets", "events")
SENTINEL = 1e300


def load_schema(kind: str, schema_dir: Path = SCHEMA_DIR) -> dict[str, Any]:
    """Load one seam schema by kind."""

    return json.loads((schema_dir / f"{kind}.schema.json").read_text(encoding="utf-8"))


def infer_kind(path: Path) -> str | None:
    """Kind from the file name (``observations_rgb.parquet`` -> observations)."""

    stem = path.stem.lower()
    return next((kind for kind in KINDS if stem.startswith(kind)), None)


def read_view(path: Path) -> pa.Table:
    """Read a Parquet or CSV view."""

    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return pq.read_table(path)
    if suffix in {".csv", ".tsv"}:
        return pacsv.read_csv(
            path,
            parse_options=pacsv.ParseOptions(
                delimiter="\t" if suffix == ".tsv" else ","
            ),
        )
    raise ValueError(f"unsupported view type: {path.name}")


def _types(spec: dict[str, Any]) -> set[str]:
    declared = spec.get("type", [])
    return {declared} if isinstance(declared, str) else set(declared)


def _compatible(arrow_type: pa.DataType, spec: dict[str, Any]) -> bool:
    types = _types(spec) - {"null"}
    if not types or pa.types.is_null(arrow_type):
        return True
    if pa.types.is_dictionary(arrow_type):
        arrow_type = arrow_type.value_type
    is_str = pa.types.is_string(arrow_type) or pa.types.is_large_string(arrow_type)
    checks = {
        "string": is_str
        or (
            spec.get("format") == "date-time"
            and (pa.types.is_timestamp(arrow_type) or pa.types.is_date(arrow_type))
        ),
        "number": pa.types.is_integer(arrow_type)
        or pa.types.is_floating(arrow_type)
        or pa.types.is_decimal(arrow_type),
        "integer": pa.types.is_integer(arrow_type),
        "boolean": pa.types.is_boolean(arrow_type),
        "array": pa.types.is_list(arrow_type) or pa.types.is_large_list(arrow_type),
        "object": pa.types.is_struct(arrow_type) or pa.types.is_map(arrow_type),
    }
    return any(checks.get(kind, False) for kind in types)


def _row_value(value: Any) -> Any:
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dt.datetime):
        return value.isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    return value


def _check_datetime(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    try:
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_table(
    table: pa.Table, schema: dict[str, Any], *, sample: int = 2000
) -> dict[str, Any]:
    """Validate one table against one row schema; returns errors and warnings."""

    errors: list[str] = []
    warnings: list[str] = []
    properties: dict[str, Any] = schema.get("properties", {})
    required = list(schema.get("required", []))
    names = set(table.column_names)
    missing = [column for column in required if column not in names]
    if missing:
        errors.append(f"missing required columns: {missing}")
    for column, spec in properties.items():
        if column not in names:
            continue
        arrow_type = table.schema.field(column).type
        if not _compatible(arrow_type, spec):
            errors.append(
                f"column {column}: storage type {arrow_type} is not compatible with schema type {spec.get('type')}"
            )
        nulls = table.column(column).null_count
        if nulls and "null" not in _types(spec) and column in required:
            errors.append(
                f"column {column}: {nulls} null values in a required, non-nullable column"
            )
        if pa.types.is_floating(arrow_type):
            values = table.column(column)
            huge = (
                pc.sum(
                    pc.cast(pc.greater_equal(pc.abs(values), SENTINEL), pa.int64())
                ).as_py()
                or 0
            )
            if huge:
                errors.append(
                    f"column {column}: {huge} sentinel-like values (|x| >= 1e300); missing must be null"
                )
            nans = pc.sum(pc.cast(pc.is_nan(values), pa.int64())).as_py() or 0
            if nans:
                warnings.append(
                    f"column {column}: {nans} NaN values (prefer null for missing)"
                )
        if spec.get("format") == "date-time" and column in names:
            arrow_type = table.schema.field(column).type
            if pa.types.is_string(arrow_type) or pa.types.is_large_string(arrow_type):
                bad = [
                    v
                    for v in table.column(column).slice(0, sample).to_pylist()
                    if v is not None and not _check_datetime(v)
                ]
                if bad:
                    errors.append(
                        f"column {column}: {len(bad)} values in the sample are not ISO 8601, e.g. {bad[0]!r}"
                    )
            elif pa.types.is_timestamp(arrow_type) and arrow_type.tz is None:
                warnings.append(
                    f"column {column}: timestamps carry no timezone; record the assumption in the card"
                )
    key = [column for column in schema.get("x-primary-key", []) if column in names]
    if key and len(key) == len(schema.get("x-primary-key", [])):
        tuples = list(zip(*(table.column(column).to_pylist() for column in key)))
        dupes = sum(count for count in Counter(tuples).values() if count > 1)
        if dupes:
            errors.append(f"primary key {key} is not unique: {dupes} rows share a key")
    row_errors: list[str] = []
    if not missing:
        validator = jsonschema.Draft202012Validator(schema)
        for index, row in enumerate(table.slice(0, sample).to_pylist()):
            clean = {name: _row_value(value) for name, value in row.items()}
            for error in validator.iter_errors(clean):
                row_errors.append(
                    f"row {index}: {'/'.join(str(p) for p in error.path) or '<row>'}: {error.message}"
                )
                if len(row_errors) >= 20:
                    break
            if len(row_errors) >= 20:
                break
    if row_errors:
        errors.append(
            f"{len(row_errors)}+ row-level schema errors in the first {sample} rows"
        )
    return {
        "rows": table.num_rows,
        "columns": table.column_names,
        "valid": not errors,
        "errors": errors,
        "row_errors": row_errors,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("views", type=Path, nargs="+")
    parser.add_argument(
        "--kind",
        choices=KINDS,
        help="shape for every view (default: from the file name)",
    )
    parser.add_argument(
        "--schemas",
        type=Path,
        default=SCHEMA_DIR,
        help="directory holding <kind>.schema.json",
    )
    parser.add_argument(
        "--sample", type=int, default=2000, help="rows to validate row-by-row"
    )
    parser.add_argument("--out", type=Path, help="write the JSON report here")
    args = parser.parse_args(argv)
    results: dict[str, Any] = {}
    ok = True
    for path in args.views:
        kind = args.kind or infer_kind(path)
        if kind is None:
            results[str(path)] = {
                "valid": False,
                "errors": [
                    f"cannot infer kind from name; pass --kind ({', '.join(KINDS)})"
                ],
            }
            ok = False
            continue
        try:
            report = validate_table(
                read_view(path), load_schema(kind, args.schemas), sample=args.sample
            )
        except (OSError, ValueError, pa.ArrowInvalid) as exc:
            report = {"valid": False, "errors": [f"{type(exc).__name__}: {exc}"]}
        report["kind"] = kind
        results[str(path)] = report
        ok = ok and report["valid"]
        print(
            f"{'VALID' if report['valid'] else 'INVALID'} {kind}: {path} rows={report.get('rows')}"
        )
        for message in report["errors"]:
            print(f"  error: {message}")
        for message in report.get("row_errors", [])[:5]:
            print(f"    {message}")
        for message in report.get("warnings", []):
            print(f"  warning: {message}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(f"full report: {args.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
