# /// script
# requires-python = ">=3.11"
# dependencies = ["pyarrow>=15", "numpy>=1.24"]
# ///
# pyright: reportAttributeAccessIssue=false
# (pyarrow.compute functions are generated at import time; there are no stubs.)
"""Audit every column of one table for common data traps.

Per column: storage type, null / NaN / empty-string fractions, all-null and
"ghost" columns (string-typed but never holding a non-empty value), constant
columns, sentinel candidates (values at or near the float limits, -9999-style
codes, and isolated extremes far outside the robust spread), zero fractions,
and strings that look numeric, date-like, or list-like. Across columns:
near-duplicate names that differ only by a rounded number (for example two
wavelength labels 0.01 apart), names equal after case/punctuation folding,
and columns whose contents are identical.

The input is only read. With ``--sample N`` only the first N rows are read, so
"all empty" means "empty in the sample" -- say so when you report it.

Usage::

    python audit_columns.py TABLE [--sample N] [--out report.json]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from itertools import pairwise
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
from _tables import configure_stdout, jsonable, read_table, write_json

FLOAT64_MAX = float(np.finfo(np.float64).max)
FLOAT32_MAX = float(np.finfo(np.float32).max)
#: Exact codes commonly used to mean "missing". Matching one is a candidate, not proof.
CODE_SENTINELS = (
    -9999.0,
    -999.0,
    -99.0,
    9999.0,
    99999.0,
    999999.0,
    -32768.0,
    32767.0,
    65535.0,
)
HUGE = 1e300
#: A value this many times larger than the bulk (p99 of |x|) is an isolated extreme.
EXTREME_RATIO = 1e3

NUMERIC_STRING = re.compile(r"^\s*[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?\s*$")
DATE_STRING = re.compile(
    r"^\s*\d{4}[-/.]\d{1,2}[-/.]\d{1,2}([ T]\d{1,2}:\d{2}(:\d{2}(\.\d+)?)?)?"
)
LIST_STRING = re.compile(r"^\s*[\[{(].*[\]})]\s*$", re.DOTALL)
NAME_NUMBER = re.compile(r"\d+(?:[p.]\d+)?")


def _number(token: str) -> float:
    return float(token.replace("p", "."))


def _string_profile(array: pa.ChunkedArray, non_null: int) -> dict[str, Any]:
    values = [value for value in array.to_pylist() if value is not None]
    stripped = [value.strip() for value in values]
    nonempty = [value for value in stripped if value]
    empty = len(stripped) - len(nonempty)
    profile: dict[str, Any] = {
        "empty_string_count": empty,
        "nonempty_count": len(nonempty),
    }
    if nonempty:
        profile["numeric_like_frac"] = sum(
            bool(NUMERIC_STRING.match(v)) for v in nonempty
        ) / len(nonempty)
        profile["date_like_frac"] = sum(
            bool(DATE_STRING.match(v)) for v in nonempty
        ) / len(nonempty)
        profile["list_like_frac"] = sum(
            bool(LIST_STRING.match(v)) for v in nonempty
        ) / len(nonempty)
        counts: dict[str, int] = defaultdict(int)
        for value in nonempty:
            counts[value] += 1
        profile["distinct"] = len(counts)
        profile["top_values"] = [
            {"value": value[:80], "count": count}
            for value, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[
                :5
            ]
        ]
    return profile


def _numeric_profile(array: pa.ChunkedArray) -> dict[str, Any]:
    data = pc.cast(array, pa.float64()).to_numpy(zero_copy_only=False)
    data = data.astype(np.float64, copy=False)
    nan_mask = np.isnan(data)
    finite = data[np.isfinite(data)]
    profile: dict[str, Any] = {
        "nan_count": int(nan_mask.sum()),
        "inf_count": int(np.isinf(data).sum()),
    }
    if finite.size == 0:
        return profile
    abs_vals = np.abs(finite)
    huge_mask = abs_vals >= HUGE
    float32_mask = np.isclose(abs_vals, FLOAT32_MAX, rtol=1e-6)
    bulk = finite[~(huge_mask | float32_mask)]
    profile.update(
        {
            "min": float(finite.min()),
            "max": float(finite.max()),
            "zero_count": int((finite == 0).sum()),
            "negative_count": int((finite < 0).sum()),
            "distinct": int(np.unique(finite).size)
            if finite.size <= 2_000_000
            else None,
        }
    )
    sentinels: list[dict[str, Any]] = []
    for label, mask in (
        ("abs>=1e300 (float64 max or near it)", huge_mask),
        ("abs==float32 max", float32_mask),
    ):
        if mask.any():
            values, counts = np.unique(finite[mask], return_counts=True)
            sentinels.append(
                {
                    "kind": label,
                    "count": int(mask.sum()),
                    "values": [
                        {"value": float(v), "count": int(c)}
                        for v, c in zip(values[:5], counts[:5])
                    ],
                }
            )
    for code in CODE_SENTINELS:
        hits = int((bulk == code).sum())
        if hits:
            sentinels.append({"kind": "code", "value": code, "count": hits})
    if bulk.size:
        median = float(np.median(bulk))
        mad = float(np.median(np.abs(bulk - median)))
        p01, p99 = (float(v) for v in np.percentile(bulk, [1, 99]))
        profile.update({"median": median, "mad": mad, "p01": p01, "p99": p99})
        scale = max(abs(p01), abs(p99), 1e-12)
        extreme_mask = np.abs(bulk) > EXTREME_RATIO * scale
        if extreme_mask.any():
            values, counts = np.unique(bulk[extreme_mask], return_counts=True)
            order = np.argsort(-counts)[:5]
            sentinels.append(
                {
                    "kind": f"isolated extreme (>{EXTREME_RATIO:g}x the p01/p99 bulk)",
                    "count": int(extreme_mask.sum()),
                    "values": [
                        {"value": float(values[i]), "count": int(counts[i])}
                        for i in order
                    ],
                }
            )
        positive_bulk = bulk[bulk != 0]
        zeros = int((bulk == 0).sum())
        if (
            zeros
            and positive_bulk.size
            and (positive_bulk > 0).all()
            and zeros / bulk.size < 0.2
        ):
            profile["zero_as_missing_candidate"] = True
    profile["sentinel_candidates"] = sentinels
    return profile


def near_duplicate_names(
    names: list[str], *, abs_tol: float = 0.05, rel_tol: float = 1e-4
) -> list[dict[str, Any]]:
    """Pairs of names whose text matches once numbers are masked and whose last
    number differs by no more than a rounding step (e.g. ``..._892p01nm`` vs
    ``..._892p02nm``), plus names equal after case/punctuation folding."""

    pairs: list[dict[str, Any]] = []
    skeletons: dict[str, list[tuple[float, str]]] = defaultdict(list)
    for name in names:
        numbers = NAME_NUMBER.findall(name)
        if not numbers:
            continue
        skeleton = NAME_NUMBER.sub("#", name)
        skeletons[skeleton].append((_number(numbers[-1]), name))
    for skeleton, members in skeletons.items():
        members.sort()
        for (value_a, name_a), (value_b, name_b) in pairwise(members):
            gap = abs(value_b - value_a)
            if name_a != name_b and gap <= max(
                abs_tol, rel_tol * max(abs(value_a), abs(value_b))
            ):
                pairs.append(
                    {
                        "a": name_a,
                        "b": name_b,
                        "kind": "rounding",
                        "number_gap": round(gap, 6),
                        "pattern": skeleton,
                    }
                )
    folded: dict[str, list[str]] = defaultdict(list)
    for name in names:
        folded[re.sub(r"[^a-z0-9]", "", name.lower())].append(name)
    for group in folded.values():
        if len(group) > 1:
            for other in group[1:]:
                pairs.append({"a": group[0], "b": other, "kind": "case_or_punctuation"})
    return pairs


def identical_columns(table: pa.Table, candidates: list[str]) -> list[list[str]]:
    """Groups of columns whose values are identical row by row (after casting to string)."""

    buckets: dict[tuple[Any, ...], list[str]] = defaultdict(list)
    for name in candidates:
        column = table.column(name)
        head = tuple(str(v) for v in column.slice(0, 20).to_pylist())
        buckets[(column.null_count, head)].append(name)
    groups: list[list[str]] = []
    for names in buckets.values():
        if len(names) < 2:
            continue
        remaining = list(names)
        while remaining:
            first = remaining.pop(0)
            reference = (
                pc.cast(table.column(first), pa.string())
                if not pa.types.is_string(table.column(first).type)
                else table.column(first)
            )
            same = [first]
            for other in list(remaining):
                column = table.column(other)
                try:
                    as_string = (
                        column
                        if pa.types.is_string(column.type)
                        else pc.cast(column, pa.string())
                    )
                except (pa.ArrowInvalid, pa.ArrowNotImplementedError):
                    continue
                if as_string.equals(reference):
                    same.append(other)
                    remaining.remove(other)
            if len(same) > 1:
                groups.append(same)
    return groups


def audit(table: pa.Table) -> dict[str, Any]:
    """Audit one in-memory table; returns the JSON-ready report."""

    rows = table.num_rows
    columns: list[dict[str, Any]] = []
    for field in table.schema:
        array = table.column(field.name)
        null_count = array.null_count
        entry: dict[str, Any] = {
            "name": field.name,
            "type": str(field.type),
            "null_count": null_count,
            "null_frac": (null_count / rows) if rows else None,
        }
        typ = field.type
        if pa.types.is_null(typ):
            entry["all_null"] = True
        elif pa.types.is_string(typ) or pa.types.is_large_string(typ):
            entry.update(_string_profile(array, rows - null_count))
            entry["all_null"] = null_count == rows
            entry["ghost_string"] = rows > 0 and entry.get("nonempty_count", 0) == 0
        elif (
            pa.types.is_integer(typ)
            or pa.types.is_floating(typ)
            or pa.types.is_decimal(typ)
        ):
            entry.update(_numeric_profile(array))
            entry["all_null"] = (
                null_count == rows or entry.get("nan_count", 0) + null_count == rows
            )
        elif pa.types.is_list(typ) or pa.types.is_large_list(typ):
            lengths = pc.list_value_length(array).to_numpy(zero_copy_only=False)
            entry["list_type"] = True
            entry["empty_list_count"] = int(np.nansum(lengths == 0))
            entry["all_null"] = null_count == rows
        else:
            entry["all_null"] = null_count == rows
        if not entry.get("all_null") and not entry.get("ghost_string"):
            try:
                distinct = pc.count_distinct(array).as_py()
            except (pa.ArrowNotImplementedError, pa.ArrowInvalid):
                distinct = None
            entry["constant"] = distinct == 1
        columns.append(entry)

    names = [c["name"] for c in columns]
    ghost = [c["name"] for c in columns if c.get("ghost_string") or c.get("all_null")]
    live = [c["name"] for c in columns if c["name"] not in ghost]
    near_dupes = near_duplicate_names(names)
    ghost_set = set(ghost)
    for pair in near_dupes:
        pair["a_empty"] = pair["a"] in ghost_set
        pair["b_empty"] = pair["b"] in ghost_set
    return {
        "rows": rows,
        "column_count": len(columns),
        "columns": columns,
        "findings": {
            "all_empty_columns": ghost,
            "ghost_string_columns": [
                c["name"] for c in columns if c.get("ghost_string")
            ],
            "constant_columns": [c["name"] for c in columns if c.get("constant")],
            "sentinel_columns": [
                {"name": c["name"], "candidates": c["sentinel_candidates"]}
                for c in columns
                if c.get("sentinel_candidates")
            ],
            "zero_as_missing_candidates": [
                c["name"] for c in columns if c.get("zero_as_missing_candidate")
            ],
            "numeric_like_string_columns": [
                c["name"] for c in columns if c.get("numeric_like_frac", 0) >= 0.95
            ],
            "date_like_string_columns": [
                c["name"] for c in columns if c.get("date_like_frac", 0) >= 0.95
            ],
            "list_like_columns": [
                c["name"]
                for c in columns
                if c.get("list_like_frac", 0) >= 0.5 or c.get("list_type")
            ],
            "near_duplicate_names": near_dupes,
            "identical_columns": identical_columns(table, live),
        },
    }


def summarize(
    report: dict[str, Any], path: str, sampled: int, limit: int = 8
) -> list[str]:
    """Short human summary of an audit report."""

    f = report["findings"]
    lines = [
        f"table: {path}  rows read: {report['rows']}{' (SAMPLE: first rows only)' if sampled else ''}  columns: {report['column_count']}",
        f"all-empty columns: {len(f['all_empty_columns'])} (string-typed ghosts: {len(f['ghost_string_columns'])}) e.g. {f['all_empty_columns'][:limit]}",
        f"constant columns: {len(f['constant_columns'])} e.g. {f['constant_columns'][:limit]}",
    ]
    for item in f["sentinel_columns"][:limit]:
        kinds = "; ".join(
            f"{c['kind']} x{c['count']}"
            + (
                f" e.g. {c['values'][0]['value']:.6g}"
                if c.get("values")
                else f" ({c.get('value')})"
            )
            for c in item["candidates"]
        )
        lines.append(f"SENTINEL candidate: {item['name']}: {kinds}")
    if len(f["sentinel_columns"]) > limit:
        lines.append(
            f"... {len(f['sentinel_columns']) - limit} more sentinel columns in the JSON"
        )
    if f["zero_as_missing_candidates"]:
        lines.append(
            f"zeros in otherwise positive columns (zero-as-missing?): {f['zero_as_missing_candidates'][:limit]}"
        )
    dupes = f["near_duplicate_names"]
    if dupes:
        lines.append(f"near-duplicate column names: {len(dupes)} pairs, e.g.")
        for pair in dupes[:limit]:
            empties = [
                n
                for n, flag in (
                    (pair["a"], pair.get("a_empty")),
                    (pair["b"], pair.get("b_empty")),
                )
                if flag
            ]
            lines.append(
                f"  {pair['a']} ~ {pair['b']} ({pair['kind']}){' empty: ' + ', '.join(empties) if empties else ''}"
            )
    if f["identical_columns"]:
        lines.append(
            f"identical-content column groups: {f['identical_columns'][:limit]}"
        )
    for key, label in (
        ("numeric_like_string_columns", "numbers stored as strings"),
        ("date_like_string_columns", "dates stored as strings"),
        ("list_like_columns", "list-like values"),
    ):
        if f[key]:
            lines.append(f"{label}: {f[key][:limit]}")
    return lines


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    configure_stdout()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("table", type=Path)
    parser.add_argument(
        "--sample", type=int, default=0, help="read only the first N rows (0 = all)"
    )
    parser.add_argument(
        "--out", type=Path, help="write the full JSON report here instead of stdout"
    )
    args = parser.parse_args(argv)
    if not args.table.is_file():
        print(f"error: no such file: {args.table}", file=sys.stderr)
        return 2
    table = read_table(args.table, sample=args.sample)
    report = audit(table)
    report["table"] = str(args.table)
    report["sample"] = args.sample
    print("\n".join(summarize(report, str(args.table), args.sample)))
    write_json(jsonable(report), args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
