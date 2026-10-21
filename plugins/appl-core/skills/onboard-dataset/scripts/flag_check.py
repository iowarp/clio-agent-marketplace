# /// script
# requires-python = ">=3.11"
# dependencies = ["pyarrow>=15"]
# ///
"""Check whether a QC/flag column agrees with the data it is meant to describe.

A row's signal is "missing" when every ``--signal`` column is null, NaN, an
empty string (or zero, with ``--zero-is-missing``, for coverage-like columns).
Flags are parsed from list-typed cells, JSON/Python-style list strings, or
``;``/``,``/``|`` separated strings.

Reports, per flag value: how many rows carry it, the share of all rows
(flags on >= 95% of rows are "universal" and useless as filters), and how
well it tracks missing signal (precision: missing | flag; recall: flag |
missing). Also counts missing-signal rows that carry no flag at all, and
rows carrying a specific (non-universal) flag whose signal is present.

The input is only read.

Usage::

    python flag_check.py TABLE --flags qc_flags --signal value [--signal other] [--out report.json]
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pyarrow as pa
from _tables import configure_stdout, jsonable, read_table, write_json

UNIVERSAL = 0.95
SPLIT = re.compile(r"[;,|]")


def parse_flags(cell: Any) -> frozenset[str]:
    """Parse one flag cell into a set of flag strings."""

    if cell is None:
        return frozenset()
    if isinstance(cell, (list, tuple, set)):
        return frozenset(
            str(item).strip() for item in cell if item is not None and str(item).strip()
        )
    text = str(cell).strip()
    if not text or text in {"[]", "{}", "()", "nan", "None", "null"}:
        return frozenset()
    if text[0] in "[({":
        for loader in (json.loads, ast.literal_eval):
            try:
                parsed = loader(text)
            except (ValueError, SyntaxError, TypeError):
                continue
            if isinstance(parsed, (list, tuple, set)):
                return parse_flags(list(parsed))
            if isinstance(parsed, dict):
                return frozenset(str(key) for key, value in parsed.items() if value)
        text = text.strip("[](){}")
    return frozenset(
        part.strip().strip("'\"")
        for part in SPLIT.split(text)
        if part.strip().strip("'\"")
    )


def _missing(value: Any, zero_is_missing: bool) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return (
        zero_is_missing
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value == 0
    )


def check(
    table: pa.Table,
    flags_column: str,
    signals: list[str],
    *,
    zero_is_missing: bool = False,
) -> dict[str, Any]:
    """Cross-tabulate flags against missing signal."""

    absent = [c for c in [flags_column, *signals] if c not in table.column_names]
    if absent:
        return {"error": f"columns not in table: {absent}"}
    rows = table.num_rows
    flag_sets = [parse_flags(cell) for cell in table.column(flags_column).to_pylist()]
    signal_values = [table.column(name).to_pylist() for name in signals]
    missing = [
        all(_missing(values[i], zero_is_missing) for values in signal_values)
        for i in range(rows)
    ]
    n_missing = sum(missing)
    per_flag: Counter[str] = Counter()
    per_flag_missing: Counter[str] = Counter()
    unflagged_missing = no_flag_rows = 0
    for flags, is_missing in zip(flag_sets, missing):
        if not flags:
            no_flag_rows += 1
            if is_missing:
                unflagged_missing += 1
        for flag in flags:
            per_flag[flag] += 1
            if is_missing:
                per_flag_missing[flag] += 1
    flag_rows = []
    for flag, count in per_flag.most_common():
        hits = per_flag_missing[flag]
        flag_rows.append(
            {
                "flag": flag,
                "rows": count,
                "row_frac": count / rows if rows else None,
                "missing_rows": hits,
                "precision": hits / count if count else None,
                "recall": hits / n_missing if n_missing else None,
                "universal": bool(rows) and count / rows >= UNIVERSAL,
            }
        )
    # A missing row is "explained" only by a flag that is not universal noise.
    specific = {row["flag"] for row in flag_rows if not row["universal"]}
    unexplained = sum(
        1 for flags, m in zip(flag_sets, missing) if m and not (flags & specific)
    )
    flagged_present = sum(
        1 for flags, m in zip(flag_sets, missing) if not m and flags & specific
    )
    return {
        "rows": rows,
        "flags_column": flags_column,
        "signal_columns": signals,
        "zero_is_missing": zero_is_missing,
        "missing_signal_rows": n_missing,
        "rows_without_any_flag": no_flag_rows,
        "missing_without_any_flag": unflagged_missing,
        "missing_without_specific_flag": unexplained,
        "flagged_but_signal_present": flagged_present,
        "flags": flag_rows,
        "universal_flags": [row["flag"] for row in flag_rows if row["universal"]],
    }


def summarize(report: dict[str, Any], limit: int = 10) -> list[str]:
    """Short human summary of a flag check."""

    if "error" in report:
        return [f"error: {report['error']}"]
    rows = report["rows"] or 1
    lines = [
        (
            f"rows: {report['rows']}  missing signal ({', '.join(report['signal_columns'])}): "
            f"{report['missing_signal_rows']} ({report['missing_signal_rows'] / rows:.1%})"
        ),
        (
            f"missing rows with NO flag: {report['missing_without_any_flag']}; "
            f"with no specific (non-universal) flag: {report['missing_without_specific_flag']}"
        ),
        f"rows with a specific flag whose signal is present: {report['flagged_but_signal_present']}",
    ]
    if report["universal_flags"]:
        lines.append(
            f"UNIVERSAL flags (>= {UNIVERSAL:.0%} of rows; useless as filters): {report['universal_flags']}"
        )
    for row in report["flags"][:limit]:
        precision = "n/a" if row["precision"] is None else f"{row['precision']:.2f}"
        recall = "n/a" if row["recall"] is None else f"{row['recall']:.2f}"
        lines.append(
            f"  {row['flag']}: rows={row['rows']} ({row['row_frac']:.1%}) precision={precision} recall={recall}"
        )
    if (
        report["missing_signal_rows"]
        and report["missing_without_specific_flag"] / report["missing_signal_rows"]
        > 0.5
    ):
        lines.append(
            "=> flags MISS most missing-signal rows: filter on the signal itself, not on the flags"
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    configure_stdout()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("table", type=Path)
    parser.add_argument("--flags", required=True, help="the flag/QC column")
    parser.add_argument(
        "--signal", action="append", required=True, help="a signal column (repeatable)"
    )
    parser.add_argument(
        "--zero-is-missing",
        action="store_true",
        help="treat 0 as missing signal (coverage-like columns)",
    )
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
    columns = [args.flags, *args.signal]
    try:
        table = read_table(args.table, sample=args.sample, columns=columns)
    except (KeyError, pa.ArrowInvalid) as exc:
        print(
            f"error: cannot read columns {columns} from {args.table}: {exc}",
            file=sys.stderr,
        )
        return 2
    report = check(table, args.flags, args.signal, zero_is_missing=args.zero_is_missing)
    report["table"] = str(args.table)
    print("\n".join(summarize(report)))
    write_json(jsonable(report), args.out)
    return 0 if "error" not in report else 1


if __name__ == "__main__":
    raise SystemExit(main())
