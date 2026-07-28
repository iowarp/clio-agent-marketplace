#!/usr/bin/env python3
"""Inventory and compare bounded OOXML/OpenDocument ZIP packages."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

MAX_ENTRIES = 20_000
MAX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_COMPRESSION_RATIO = 250.0


def inventory(path: Path) -> dict[str, Any]:
    """Return a deterministic, security-bounded package inventory."""

    result: dict[str, Any] = {"path": str(path.resolve()), "parts": {}}
    total = 0
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ENTRIES:
            raise ValueError("package has too many entries")
        for info in infos:
            name = PurePosixPath(info.filename)
            if name.is_absolute() or ".." in name.parts:
                raise ValueError(f"unsafe package path: {info.filename}")
            total += info.file_size
            if total > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("package exceeds the uncompressed size limit")
            if info.compress_size == 0 and info.file_size:
                raise ValueError(f"invalid compression ratio: {info.filename}")
            if (
                info.compress_size
                and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO
            ):
                raise ValueError(f"unsafe compression ratio: {info.filename}")
            payload = archive.read(info)
            result["parts"][info.filename] = {
                "size": info.file_size,
                "crc32": f"{info.CRC:08x}",
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
    result["part_count"] = len(result["parts"])
    result["uncompressed_bytes"] = total
    return result


def compare(
    before: dict[str, Any],
    after: dict[str, Any],
    allowed_patterns: list[str],
) -> dict[str, Any]:
    """Compare inventories and classify unallowed package drift."""

    before_parts = dict(before.get("parts", {}))
    after_parts = dict(after.get("parts", {}))

    def allowed(name: str) -> bool:
        return any(fnmatch.fnmatchcase(name, pattern) for pattern in allowed_patterns)

    removed = sorted(set(before_parts) - set(after_parts))
    added = sorted(set(after_parts) - set(before_parts))
    changed = sorted(
        name
        for name in set(before_parts) & set(after_parts)
        if before_parts[name].get("sha256") != after_parts[name].get("sha256")
    )
    unexpected = sorted(
        name for name in [*removed, *added, *changed] if not allowed(name)
    )
    return {
        "ok": not unexpected,
        "removed": removed,
        "added": added,
        "changed": changed,
        "allowed_patterns": allowed_patterns,
        "unexpected": unexpected,
    }


def _write_json(path: Path | None, payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    if path is None:
        print(serialized)
    else:
        path.write_text(f"{serialized}\n", encoding="utf-8")


def main() -> int:
    """Run the inventory or comparison command."""

    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    inventory_parser = subcommands.add_parser("inventory")
    inventory_parser.add_argument("package", type=Path)
    inventory_parser.add_argument("--output", type=Path)
    compare_parser = subcommands.add_parser("compare")
    compare_parser.add_argument("before", type=Path)
    compare_parser.add_argument("package", type=Path)
    compare_parser.add_argument("--allow", action="append", default=[])
    compare_parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.command == "inventory":
        _write_json(args.output, inventory(args.package))
        return 0
    before = json.loads(args.before.read_text(encoding="utf-8"))
    outcome = compare(before, inventory(args.package), list(args.allow))
    _write_json(args.output, outcome)
    return 0 if outcome["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
