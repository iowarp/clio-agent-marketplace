# /// script
# requires-python = ">=3.11"
# dependencies = ["pyarrow>=15"]
# ///
"""Inventory a dataset directory without reading table contents.

Walks every file under ROOT and reports sizes and types, Parquet schemas and
row counts (from Parquet metadata only), CSV/TSV headers, documentation and
column-catalog candidates, and -- when a ``manifest.json`` is present -- the
manifest's SHA-256, its top-level identity keys, and any row counts it
declares compared with the counts the files actually hold.

This script only reads the input directory. Agent artefacts (experiment
card, loader, views, audit reports) live by default in the workspace store
(``<workspace_state>/datasets/<key>/``, see ``card.py``). A ``.clio``
directory at the bundle root (left by an older session, or because the user
chose the bundle itself as the store) is reported as ``legacy_agent_dir`` and
never inventoried as data.

Usage::

    python inventory.py ROOT [--out report.json] [--count-csv-rows]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pyarrow.parquet as pq
from _tables import (
    TABLE_SUFFIXES,
    configure_stdout,
    sha256_file,
    write_json,
)

DOC_SUFFIXES = frozenset({".md", ".rst", ".txt", ".pdf", ".html", ".yaml", ".yml"})
DOC_NAME = re.compile(
    r"(readme|codebook|dictionary|glossary|about|notes|license|changelog)",
    re.IGNORECASE,
)
CATALOG_NAME = re.compile(
    r"(columns?|dictionary|codebook|schema|variables|catalog)", re.IGNORECASE
)
ROW_KEY = re.compile(
    r"(^|_)(rows?|row_counts?|n_rows|num_rows|nrows|record_count)($|_)", re.IGNORECASE
)
MANIFEST_NAMES = ("manifest.json", "MANIFEST.json")
IDENTITY_KEYS = (
    "export_version",
    "version",
    "schema_version",
    "generated_at",
    "created_at",
)
LEGACY_AGENT_DIR = ".clio"  # agent artefacts at the bundle root; skipped as data


def norm_rel(value: str) -> str:
    """Normalise a manifest-relative path to POSIX form without a ``./`` prefix."""

    text = str(value).replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text


def _is_table_path(value: Any) -> bool:
    return isinstance(value, str) and Path(value).suffix.lower() in TABLE_SUFFIXES


def _walk_json(node: Any, pointer: str = "") -> Iterator[tuple[str, Any]]:
    """Yield ``(json_pointer, node)`` for every dict and list in a JSON document."""

    yield pointer, node
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                escaped = str(key).replace("~", "~0").replace("/", "~1")
                yield from _walk_json(value, f"{pointer}/{escaped}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            if isinstance(value, (dict, list)):
                yield from _walk_json(value, f"{pointer}/{index}")


def declared_table_counts(manifest: Any) -> list[dict[str, Any]]:
    """Find row counts a manifest declares for table files.

    Two generic shapes are recognised, whatever the manifest's own layout:

    * one object holding exactly one table path and an integer under a
      row-count-like key (``rows``, ``row_count``, ``n_rows`` ...);
    * sibling mappings ``{name: path}`` and ``{name: count}`` (the count
      mapping's key names rows), paired by name.

    Returns rows of ``{"path", "declared_rows", "pointer"}``; ``pointer`` is the
    JSON pointer of the count, so a tool can update it consistently.
    """

    found: list[dict[str, Any]] = []
    for pointer, node in _walk_json(manifest):
        if not isinstance(node, dict):
            continue
        paths = [key for key, value in node.items() if _is_table_path(value)]
        counts = [
            key
            for key, value in node.items()
            if ROW_KEY.search(str(key))
            and isinstance(value, int)
            and not isinstance(value, bool)
        ]
        if len(paths) == 1 and len(counts) == 1:
            found.append(
                {
                    "path": node[paths[0]],
                    "declared_rows": node[counts[0]],
                    "pointer": f"{pointer}/{counts[0]}",
                }
            )
        path_maps = {
            key: value
            for key, value in node.items()
            if isinstance(value, dict)
            and value
            and all(_is_table_path(v) for v in value.values())
        }
        count_maps = {
            key: value
            for key, value in node.items()
            if ROW_KEY.search(str(key))
            and isinstance(value, dict)
            and value
            and all(
                isinstance(v, int) and not isinstance(v, bool) for v in value.values()
            )
        }
        for path_key, path_map in path_maps.items():
            for count_key, count_map in count_maps.items():
                for name, path in path_map.items():
                    if name in count_map:
                        found.append(
                            {
                                "path": path,
                                "declared_rows": count_map[name],
                                "pointer": f"{pointer}/{count_key}/{name}",
                                "logical_name": name,
                                "path_pointer": f"{pointer}/{path_key}/{name}",
                            }
                        )
    return found


def referenced_paths(manifest: Any) -> set[str]:
    """Every string in the manifest that looks like a table path."""

    refs: set[str] = set()
    for _, node in _walk_json(manifest):
        values = node.values() if isinstance(node, dict) else node
        for value in values:
            if _is_table_path(value):
                refs.add(norm_rel(value))
    return refs


def _parquet_info(path: Path) -> dict[str, Any]:
    try:
        parquet = pq.ParquetFile(path)
    except Exception as exc:  # noqa: BLE001 - a corrupt file is a finding, not a crash
        return {"error": f"{type(exc).__name__}: {exc}"}
    schema = parquet.schema_arrow
    return {
        "rows": parquet.metadata.num_rows,
        "row_groups": parquet.metadata.num_row_groups,
        "columns": len(schema),
        "schema": [{"name": field.name, "type": str(field.type)} for field in schema],
    }


def _csv_info(path: Path, count_rows: bool) -> dict[str, Any]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            header = next(csv.reader(handle, delimiter=delimiter), [])
            info: dict[str, Any] = {"columns": len(header), "header": header}
            if count_rows:
                info["rows"] = sum(1 for _ in csv.reader(handle, delimiter=delimiter))
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    return info


def inventory(root: Path, *, count_csv_rows: bool = False) -> dict[str, Any]:
    """Build the inventory report for one dataset root."""

    root = root.resolve()
    by_extension: dict[str, dict[str, int]] = defaultdict(
        lambda: {"files": 0, "bytes": 0}
    )
    by_directory: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"files": 0, "bytes": 0, "extensions": defaultdict(int)}
    )
    tables: list[dict[str, Any]] = []
    docs: list[dict[str, Any]] = []
    total_files = total_bytes = 0
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        if current == root and LEGACY_AGENT_DIR in dirnames:
            dirnames.remove(LEGACY_AGENT_DIR)
        dirnames.sort()
        rel_dir = current.relative_to(root).as_posix() or "."
        for name in sorted(filenames):
            path = current / name
            try:
                size = path.stat().st_size
            except OSError:
                continue
            suffix = path.suffix.lower() or "<none>"
            total_files += 1
            total_bytes += size
            by_extension[suffix]["files"] += 1
            by_extension[suffix]["bytes"] += size
            by_directory[rel_dir]["files"] += 1
            by_directory[rel_dir]["bytes"] += size
            by_directory[rel_dir]["extensions"][suffix] += 1
            rel = path.relative_to(root).as_posix()
            if suffix in TABLE_SUFFIXES:
                entry: dict[str, Any] = {
                    "path": rel,
                    "format": suffix.lstrip("."),
                    "bytes": size,
                }
                if suffix in {".parquet", ".pq"}:
                    entry.update(_parquet_info(path))
                else:
                    entry.update(_csv_info(path, count_csv_rows))
                entry["column_catalog_candidate"] = bool(CATALOG_NAME.search(path.stem))
                tables.append(entry)
            elif suffix in DOC_SUFFIXES and (
                "doc" in rel.lower() or DOC_NAME.search(name) or rel_dir == "."
            ):
                docs.append({"path": rel, "bytes": size})

    stems: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for table in tables:
        stems[str(Path(table["path"]).with_suffix(""))].append(table)
    for group in stems.values():
        if len(group) > 1:
            for table in group:
                table["twins"] = [
                    other["path"] for other in group if other is not table
                ]
                rows = {
                    other.get("rows")
                    for other in group
                    if other.get("rows") is not None
                }
                if len(rows) > 1:
                    table["twin_row_count_mismatch"] = sorted(
                        int(r) for r in rows if r is not None
                    )

    directories = [
        {
            "path": path,
            "files": stats["files"],
            "bytes": stats["bytes"],
            "extensions": dict(
                sorted(stats["extensions"].items(), key=lambda kv: -kv[1])
            ),
        }
        for path, stats in sorted(by_directory.items())
    ]
    report: dict[str, Any] = {
        "root": str(root),
        "totals": {"files": total_files, "bytes": total_bytes},
        "by_extension": dict(
            sorted(by_extension.items(), key=lambda kv: -kv[1]["bytes"])
        ),
        "directories": directories,
        "tables": tables,
        "docs": docs,
        "legacy_agent_dir": {
            "path": LEGACY_AGENT_DIR,
            "exists": (root / LEGACY_AGENT_DIR).is_dir(),
        },
        "manifest": _manifest_report(root, tables),
    }
    return report


def _manifest_report(root: Path, tables: list[dict[str, Any]]) -> dict[str, Any] | None:
    path = next(
        (root / name for name in MANIFEST_NAMES if (root / name).is_file()), None
    )
    if path is None:
        return None
    report: dict[str, Any] = {"path": path.name, "sha256": sha256_file(path)}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        return report
    if isinstance(manifest, dict):
        report["top_level_keys"] = sorted(manifest)
        report["identity"] = {
            key: manifest[key]
            for key in IDENTITY_KEYS
            if key in manifest and not isinstance(manifest[key], (dict, list))
        }
    actual = {table["path"]: table.get("rows") for table in tables}
    comparisons = []
    for declared in declared_table_counts(manifest):
        rel = norm_rel(declared["path"])
        rows = actual.get(rel)
        if rel not in actual:
            status = "file_missing"
        elif rows is None:
            status = "not_counted"
        elif rows == declared["declared_rows"]:
            status = "match"
        else:
            status = "mismatch"
        comparisons.append({**declared, "actual_rows": rows, "status": status})
    report["declared_counts"] = comparisons
    refs = referenced_paths(manifest)
    report["referenced_missing"] = sorted(ref for ref in refs if ref not in actual)
    report["unreferenced_tables"] = sorted(
        path
        for path in actual
        if path not in refs and Path(path).suffix.lower() in {".parquet", ".pq"}
    )
    return report


def _human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def summarize(report: dict[str, Any], limit: int = 8) -> list[str]:
    """Short human summary of an inventory report."""

    lines = [
        f"root: {report['root']}",
        f"files: {report['totals']['files']}  size: {_human(report['totals']['bytes'])}",
    ]
    heavy = sorted(report["directories"], key=lambda d: -d["bytes"])[:limit]
    lines.append(
        "largest directories: "
        + ", ".join(
            f"{d['path']} ({_human(d['bytes'])}, {d['files']} files)" for d in heavy
        )
    )
    tables = report["tables"]
    parquet = [t for t in tables if t["format"] in {"parquet", "pq"}]
    lines.append(
        f"tables: {len(tables)} ({len(parquet)} Parquet, {len(tables) - len(parquet)} CSV/TSV)"
    )
    errors = [t for t in tables if "error" in t]
    if errors:
        lines.append(
            f"UNREADABLE tables: {len(errors)} e.g. {errors[0]['path']}: {errors[0]['error']}"
        )
    twin_bad = [t["path"] for t in tables if "twin_row_count_mismatch" in t]
    if twin_bad:
        lines.append(f"twin files with different row counts: {twin_bad[:limit]}")
    catalogs = [t["path"] for t in tables if t.get("column_catalog_candidate")]
    if catalogs:
        lines.append(f"column-catalog candidates ({len(catalogs)}): {catalogs[:limit]}")
    lines.append(
        f"docs: {len(report['docs'])} e.g. {[d['path'] for d in report['docs'][:limit]]}"
    )
    if report["legacy_agent_dir"]["exists"]:
        lines.append(
            ".clio dir in the bundle: skipped as agent artefacts, not data "
            "(find the card with card.py status --store STORE)"
        )
    manifest = report.get("manifest")
    if manifest is None:
        lines.append("manifest: none found at root")
    else:
        lines.append(f"manifest: {manifest['path']} sha256={manifest['sha256']}")
        if "error" in manifest:
            lines.append(f"manifest UNREADABLE: {manifest['error']}")
        if manifest.get("identity"):
            lines.append(f"manifest identity: {manifest['identity']}")
        counts = manifest.get("declared_counts", [])
        bad = [c for c in counts if c["status"] != "match"]
        lines.append(
            f"declared row counts: {len(counts)} checked, {len(bad)} not matching"
        )
        for item in bad[:limit]:
            lines.append(
                f"  {item['status']}: {item['path']} declared={item['declared_rows']} actual={item['actual_rows']}"
            )
        if manifest.get("referenced_missing"):
            lines.append(
                f"manifest references missing files: {manifest['referenced_missing'][:limit]}"
            )
        if manifest.get("unreferenced_tables"):
            lines.append(
                f"Parquet tables the manifest does not reference: {manifest['unreferenced_tables'][:limit]}"
            )
    return lines


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    configure_stdout()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("root", type=Path)
    parser.add_argument(
        "--out", type=Path, help="write the full JSON report here instead of stdout"
    )
    parser.add_argument(
        "--count-csv-rows", action="store_true", help="count CSV rows (reads every CSV)"
    )
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        print(f"error: not a directory: {args.root}", file=sys.stderr)
        return 2
    report = inventory(args.root, count_csv_rows=args.count_csv_rows)
    print("\n".join(summarize(report)))
    write_json(report, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
