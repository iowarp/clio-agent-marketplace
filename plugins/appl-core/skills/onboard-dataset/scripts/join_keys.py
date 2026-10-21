# /// script
# requires-python = ">=3.11"
# dependencies = ["pyarrow>=15"]
# ///
"""Check whether two tables can be joined on a key, before joining them.

Reports, per side: key storage types, value "shapes" (digits -> 9, letters ->
a/A, runs collapsed, so ``ab__123__X1`` becomes ``a__9__A9``), letter case,
key uniqueness (duplicate keys fan a join out), and the overlap between the
two sides (distinct keys and rows matched on each side). When a single key
column shares few or no values, it tries simple normalisations (case folding,
trimming, the leading ``__``/``_``/``-``/``:`` separated tokens) and lists
other same-named columns whose values do overlap, as join-key candidates.

Both inputs are only read.

Usage::

    python join_keys.py TABLE_A TABLE_B --keys col1,col2 [--out report.json]
    python join_keys.py TABLE_A TABLE_B --key-column sample_key
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pyarrow as pa
import pyarrow.parquet as pq
from _tables import configure_stdout, jsonable, read_table, write_json

SEPARATORS = re.compile(r"(__|_|-|:|/|\.)")
LOW_OVERLAP = 0.5


def shape(value: Any) -> str:
    """Collapse a key value into its character-class shape."""

    text = str(value)
    out: list[str] = []
    for char in text:
        if char.isdigit():
            cls = "9"
        elif char.isalpha():
            cls = "A" if char.isupper() else "a"
        else:
            cls = char
        if not out or out[-1] != cls or cls not in "9aA":
            out.append(cls)
    return "".join(out)


def _case(values: Iterable[str]) -> str:
    kinds = set()
    for value in values:
        letters = [c for c in value if c.isalpha()]
        if not letters:
            continue
        if all(c.isupper() for c in letters):
            kinds.add("upper")
        elif all(c.islower() for c in letters):
            kinds.add("lower")
        else:
            kinds.add("mixed")
    return "+".join(sorted(kinds)) or "no letters"


def _key_tuples(table: pa.Table, keys: list[str]) -> list[tuple[Any, ...]]:
    columns = [table.column(key).to_pylist() for key in keys]
    return list(zip(*columns))


def _side_report(
    table: pa.Table, keys: list[str], tuples: list[tuple[Any, ...]]
) -> dict[str, Any]:
    counts = Counter(tuples)
    report: dict[str, Any] = {
        "rows": table.num_rows,
        "types": {key: str(table.schema.field(key).type) for key in keys},
        "null_key_rows": sum(1 for t in tuples if any(v is None for v in t)),
        "distinct_keys": len(counts),
        "duplicate_key_rows": sum(c for c in counts.values() if c > 1),
        "max_rows_per_key": max(counts.values()) if counts else 0,
        "per_column": {},
    }
    for index, key in enumerate(keys):
        values = [str(t[index]) for t in tuples if t[index] is not None]
        shapes = Counter(shape(v) for v in values)
        report["per_column"][key] = {
            "shapes": [{"shape": s, "count": c} for s, c in shapes.most_common(5)],
            "shape_count": len(shapes),
            "case": _case(values[:50000]),
            "examples": sorted(set(values))[:3],
        }
    return report


def _normalised_overlap(a: list[str], b: list[str]) -> list[dict[str, Any]]:
    set_a, set_b = set(a), set(b)
    trials: list[dict[str, Any]] = []

    def trial(label: str, fa: Any, fb: Any = None) -> None:
        fb = fb or fa
        na = {fa(v) for v in set_a}
        nb = {fb(v) for v in set_b}
        common = len(na & nb)
        if common:
            trials.append(
                {
                    "normalisation": label,
                    "shared_distinct": common,
                    "of_a": len(na),
                    "of_b": len(nb),
                }
            )

    trial("casefold+strip", lambda v: v.strip().casefold())
    for n_tokens in (1, 2, 3, 4):

        def head(v: str, n: int = n_tokens) -> str:
            parts = [
                p
                for p in SEPARATORS.split(v.strip().casefold())
                if p and not SEPARATORS.fullmatch(p)
            ]
            return "|".join(parts[:n])

        trial(f"first {n_tokens} token(s) (casefolded)", head)
    return trials


def compare(table_a: pa.Table, table_b: pa.Table, keys: list[str]) -> dict[str, Any]:
    """Compare key columns ``keys`` (present in both tables)."""

    missing = {
        side: [k for k in keys if k not in table.column_names]
        for side, table in (("a", table_a), ("b", table_b))
    }
    if missing["a"] or missing["b"]:
        return {"error": "key columns missing", "missing": missing}
    tuples_a = _key_tuples(table_a, keys)
    tuples_b = _key_tuples(table_b, keys)
    set_a, set_b = set(tuples_a), set(tuples_b)
    shared = set_a & set_b
    report: dict[str, Any] = {
        "keys": keys,
        "a": _side_report(table_a, keys, tuples_a),
        "b": _side_report(table_b, keys, tuples_b),
        "overlap": {
            "shared_distinct_keys": len(shared),
            "only_in_a": len(set_a - set_b),
            "only_in_b": len(set_b - set_a),
            "a_rows_matched": sum(1 for t in tuples_a if t in shared),
            "b_rows_matched": sum(1 for t in tuples_b if t in shared),
        },
        "warnings": [],
    }
    warnings: list[str] = report["warnings"]
    for key in keys:
        ta, tb = report["a"]["types"][key], report["b"]["types"][key]
        if ta != tb:
            warnings.append(
                f"type mismatch on {key}: {ta} vs {tb} (cast before joining; '1' != 1)"
            )
        ca = report["a"]["per_column"][key]["case"]
        cb = report["b"]["per_column"][key]["case"]
        if ca != cb:
            warnings.append(f"letter case differs on {key}: {ca} vs {cb}")
        sa = {s["shape"] for s in report["a"]["per_column"][key]["shapes"]}
        sb = {s["shape"] for s in report["b"]["per_column"][key]["shapes"]}
        if sa and sb and not sa & sb:
            warnings.append(
                f"no common value shape on {key}: {sorted(sa)[:3]} vs {sorted(sb)[:3]}"
            )
    if report["a"]["duplicate_key_rows"] and report["b"]["duplicate_key_rows"]:
        warnings.append(
            "keys repeat on BOTH sides: a join multiplies rows (many-to-many)"
        )
    smaller = min(len(set_a), len(set_b)) or 1
    if len(shared) / smaller < LOW_OVERLAP:
        warnings.append(
            f"low overlap: {len(shared)} shared of {smaller} distinct keys on the smaller side"
        )
        if len(keys) == 1:
            values_a = [str(t[0]) for t in tuples_a if t[0] is not None]
            values_b = [str(t[0]) for t in tuples_b if t[0] is not None]
            report["normalisation_trials"] = _normalised_overlap(values_a, values_b)
        report["alternative_keys"] = _alternative_keys(table_a, table_b, set(keys))
    return report


def _alternative_keys(
    table_a: pa.Table, table_b: pa.Table, exclude: set[str]
) -> list[dict[str, Any]]:
    """Same-named columns whose distinct values overlap well: join-key candidates."""

    candidates = []
    for name in sorted(set(table_a.column_names) & set(table_b.column_names) - exclude):
        va = {str(v) for v in table_a.column(name).to_pylist() if v is not None}
        vb = {str(v) for v in table_b.column(name).to_pylist() if v is not None}
        if len(va) < 2 or len(vb) < 2:
            continue
        shared = len(va & vb)
        frac = shared / (min(len(va), len(vb)) or 1)
        if frac >= LOW_OVERLAP:
            candidates.append(
                {
                    "column": name,
                    "shared_distinct": shared,
                    "a_distinct": len(va),
                    "b_distinct": len(vb),
                    "overlap_frac": round(frac, 4),
                }
            )
    candidates.sort(key=lambda c: (-c["overlap_frac"], -c["a_distinct"]))
    return candidates[:15]


def _column_names(path: Path) -> list[str] | None:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return list(pq.read_schema(path).names)
    return None


def _shared_column_names(a: Path, b: Path) -> set[str] | None:
    """Columns both tables carry (only these can be keys), or None if unknown."""

    names_a, names_b = _column_names(a), _column_names(b)
    if names_a is None or names_b is None:
        return None
    return set(names_a) & set(names_b)


def _present(path: Path, wanted: list[str] | None) -> list[str] | None:
    names = _column_names(path)
    if wanted is None or names is None:
        return None
    return [name for name in wanted if name in names]


def summarize(report: dict[str, Any], limit: int = 6) -> list[str]:
    """Short human summary of a join-key report."""

    if "error" in report:
        return [f"error: {report['error']} {report['missing']}"]
    o = report["overlap"]
    lines = [f"keys: {report['keys']}"]
    for side in ("a", "b"):
        s = report[side]
        shapes = {
            k: [x["shape"] for x in v["shapes"][:2]] for k, v in s["per_column"].items()
        }
        lines.append(
            f"{side}: rows={s['rows']} distinct={s['distinct_keys']} dup_rows={s['duplicate_key_rows']} "
            f"null_keys={s['null_key_rows']} types={s['types']} shapes={shapes}"
        )
    lines.append(
        f"overlap: shared={o['shared_distinct_keys']} only_a={o['only_in_a']} only_b={o['only_in_b']} "
        f"a_rows_matched={o['a_rows_matched']} b_rows_matched={o['b_rows_matched']}"
    )
    lines.extend(f"WARNING: {w}" for w in report["warnings"])
    for trial in report.get("normalisation_trials", [])[:limit]:
        lines.append(
            f"normalisation '{trial['normalisation']}' shares {trial['shared_distinct']} values"
        )
    if report.get("alternative_keys"):
        lines.append(
            "candidate join columns: "
            + ", ".join(
                f"{c['column']} ({c['overlap_frac']:.0%})"
                for c in report["alternative_keys"][:limit]
            )
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    configure_stdout()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("table_a", type=Path)
    parser.add_argument("table_b", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--keys", help="comma-separated key columns present in both tables"
    )
    group.add_argument("--key-column", help="one key column present in both tables")
    parser.add_argument(
        "--out", type=Path, help="write the full JSON report here instead of stdout"
    )
    args = parser.parse_args(argv)
    for path in (args.table_a, args.table_b):
        if not path.is_file():
            print(f"error: no such file: {path}", file=sys.stderr)
            return 2
    keys = [k.strip() for k in (args.keys or args.key_column).split(",") if k.strip()]
    shared = _shared_column_names(args.table_a, args.table_b)
    wanted = sorted(shared | set(keys)) if shared is not None else None
    report = compare(
        read_table(args.table_a, columns=_present(args.table_a, wanted)),
        read_table(args.table_b, columns=_present(args.table_b, wanted)),
        keys,
    )
    report["table_a"], report["table_b"] = str(args.table_a), str(args.table_b)
    print("\n".join(summarize(report)))
    write_json(jsonable(report), args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
