# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Profile a delimited station catalog, then write a normalized copy.

Station catalogs come with surprises: unit labels in a second header row,
two columns with the same name, longitudes in [0, 360), a column called
"Longitude" that holds something else. This script never guesses which column
is which. ``profile`` reports, for every column (by name and by ``#index``),
how many values parse as numbers and their range, flags header-like rows and
duplicate names, and lists which columns *could* be a latitude or a longitude.
``write`` takes the columns you chose (from the profile and the catalog's
documentation) and writes ``id,latitude,longitude[,height]`` with only rows
whose coordinates are in range, reporting every dropped row by reason.

    uv run --no-project station_catalog.py profile CATALOG.csv [--out profile.json]
    uv run --no-project station_catalog.py write CATALOG.csv --id COL --lat COL --lon COL \
        [--height COL] [--wrap-longitude] -o NORMALIZED.csv [--out report.json]

A column is named by its header text or by ``#N`` (zero-based position), which
is the only way to pick one of two columns that share a name. The input file is
only read.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def read_rows(path: Path) -> tuple[list[str], list[list[str]], str]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    sample = text[:65536]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
    rows = [
        row
        for row in csv.reader(text.splitlines(), delimiter=delimiter)
        if any(c.strip() for c in row)
    ]
    if not rows:
        raise SystemExit("empty catalog")
    return [h.strip() for h in rows[0]], rows[1:], delimiter


def number(text: str) -> float | None:
    try:
        value = float(text.strip())
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def column_index(header: list[str], ref: str) -> int:
    if ref.startswith("#") and ref[1:].isdigit():
        index = int(ref[1:])
        if index >= len(header):
            raise SystemExit(f"{ref}: the catalog has {len(header)} columns")
        return index
    matches = [i for i, name in enumerate(header) if name == ref]
    if not matches:
        raise SystemExit(f"{ref!r} is not a column; profile the catalog to see the names")
    if len(matches) > 1:
        raise SystemExit(
            f"{ref!r} names columns {['#%d' % i for i in matches]}; choose one by #index"
        )
    return matches[0]


def profile(path: Path) -> dict[str, Any]:
    header, rows, delimiter = read_rows(path)
    counts = Counter(header)
    columns = []
    width = len(header)
    numeric_per_row = [sum(number(c) is not None for c in row) for row in rows]
    typical = sorted(numeric_per_row)[len(numeric_per_row) // 2] if rows else 0
    header_like = [i + 2 for i, n in enumerate(numeric_per_row) if typical and n == 0]
    ragged = [i + 2 for i, row in enumerate(rows) if len(row) != width]
    skip = {line - 2 for line in header_like}
    for index, name in enumerate(header):
        values = [row[index] for i, row in enumerate(rows) if index < len(row) and i not in skip]
        parsed = [v for v in (number(x) for x in values) if v is not None]
        roles = []
        if parsed and len(parsed) >= 0.9 * len(values):

            def share(low: float, high: float) -> tuple[float, int]:
                inside = sum(low <= v <= high for v in parsed)
                return inside / len(parsed), len(parsed) - inside

            for role, low, high in (
                ("latitude", -90, 90),
                ("longitude", -180, 180),
                ("longitude in [0, 360)", 0, 360),
            ):
                fraction, outside = share(low, high)
                if fraction >= 0.5 and not (
                    role.endswith("360)") and "longitude?" in " ".join(roles) and outside == 0
                ):
                    roles.append(
                        f"{role}?"
                        + (f" ({outside} values outside [{low}, {high}])" if outside else "")
                    )
            if not roles:
                roles.append("not a coordinate in degrees")
        columns.append(
            {
                "ref": f"#{index}",
                "name": name,
                "duplicate_name": counts[name] > 1,
                "values": len(values),
                "numeric": len(parsed),
                "min": min(parsed) if parsed else None,
                "max": max(parsed) if parsed else None,
                "distinct": len(set(values)),
                "examples": values[:3],
                "could_be": roles,
            }
        )
    return {
        "path": str(path),
        "delimiter": delimiter,
        "rows": len(rows),
        "columns": columns,
        "column_values_exclude_header_like_rows": True,
        "header_like_rows": header_like[:50],
        "ragged_rows": ragged[:50],
        "notes": [
            "Ranges only say what a column could be. Confirm which column is latitude, longitude "
            "and height from the catalog's documentation and from known stations before writing.",
        ],
    }


def write(args: argparse.Namespace) -> dict[str, Any]:
    source = Path(args.catalog).resolve()
    out = Path(args.output).resolve()
    if out == source:
        raise SystemExit("write the normalized catalog to a new file")
    header, rows, _ = read_rows(source)
    refs = {"id": args.id, "latitude": args.lat, "longitude": args.lon}
    if args.height:
        refs["height"] = args.height
    index = {role: column_index(header, ref) for role, ref in refs.items()}
    dropped: Counter[str] = Counter()
    wrapped = 0
    kept: list[list[Any]] = []
    seen: Counter[str] = Counter()
    for row in rows:
        if max(index.values()) >= len(row):
            dropped["short row"] += 1
            continue
        station = row[index["id"]].strip()
        lat, lon = number(row[index["latitude"]]), number(row[index["longitude"]])
        if lat is None or lon is None:
            dropped["non-numeric coordinate (header-like or missing)"] += 1
            continue
        if not station:
            dropped["empty id"] += 1
            continue
        if not -90 <= lat <= 90:
            dropped["latitude out of range"] += 1
            continue
        if args.wrap_longitude and 180 < lon < 360:
            lon -= 360
            wrapped += 1
        if not -180 <= lon <= 180:
            dropped["longitude out of range"] += 1
            continue
        record: list[Any] = [station, lat, lon]
        if "height" in index:
            record.append(number(row[index["height"]]))
        seen[station] += 1
        kept.append(record)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "latitude", "longitude", *(["height"] if "height" in index else [])])
        writer.writerows(kept)
    return {
        "source": str(source),
        "output": str(out),
        "columns_used": {role: f"#{i} {header[i]!r}" for role, i in index.items()},
        "input_rows": len(rows),
        "written_rows": len(kept),
        "dropped": dict(dropped),
        "longitudes_wrapped_from_0_360": wrapped,
        "duplicate_ids": sorted(k for k, n in seen.items() if n > 1)[:50],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("profile")
    p.add_argument("catalog")
    p.add_argument("--out")
    w = sub.add_parser("write")
    w.add_argument("catalog")
    w.add_argument("--id", required=True)
    w.add_argument("--lat", required=True)
    w.add_argument("--lon", required=True)
    w.add_argument("--height")
    w.add_argument("--wrap-longitude", action="store_true", help="map (180, 360) to (-180, 0)")
    w.add_argument("-o", "--output", required=True)
    w.add_argument("--out")
    args = parser.parse_args(argv)
    report = profile(Path(args.catalog)) if args.command == "profile" else write(args)
    text = json.dumps(report, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
