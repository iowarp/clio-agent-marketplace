#!/usr/bin/env python3
"""Reject dataset-specific literals ("L3 leakage") in marketplace pack prompts.

Skills and experts should encode checks, not facts about one dataset or
experiment. Two mechanisms catch leaked facts:

* ``<pack>/lint-denylist.txt`` -- one literal per line (``#`` starts a comment
  line). Any occurrence in a scanned file is an error. Always enforced.
* Generic strict rules (ISO dates, measured magnitudes, sample keys, concrete
  dataset file names). Enforced only for packs that contain a ``.lint-l3``
  marker file or are named with ``--strict-pack``.

A line containing ``lint: allow-literal`` is never reported.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

DENYLIST_FILE = "lint-denylist.txt"
STRICT_MARKER = ".lint-l3"
ALLOW_MARKER = "lint: allow-literal"

# Top-level repository directories that are not packs.
_NON_PACK_DIRS = frozenset({"old", "scripts", "tests"})
# Directories inside a pack that hold test data rather than shipped prompts.
_SKIPPED_PACK_DIRS = frozenset({"tests", "evals", "fixtures", "fixture", "__pycache__"})
_BINARY_PROBE_BYTES = 8192

_ISO_DATE = re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b")
_NUM = r"\d[\d.,]*"
_RANGE = rf"{_NUM}\s*(?:[–—-]\s*{_NUM}\s*)?"
_MAGNITUDE = re.compile(
    # ~40x, ~40×, ~30-50x
    rf"~\s*{_RANGE}[x×X](?![0-9A-Za-z])"
    # 40×, 30–50× (the multiplication sign is unambiguous)
    rf"|(?<![\w.,]){_RANGE}×"
    # 40x too small, 3x larger, ...
    rf"|(?<![\w.,]){_RANGE}[xX]\s+(?:too|larger|smaller|bigger|higher|lower|"
    r"greater|more|less|off)\b"
)
_SAMPLE_KEY = re.compile(r"\b\d{2,}__\d{3,}__\d{3,}")
_DATA_FILE = re.compile(
    r"[A-Za-z0-9_<>{}*$~./-]+\.(?:parquet|csv|h5|nc|zarr)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
_TEMPLATE_CHARS = frozenset("<>{}*$")


@dataclass(frozen=True)
class LiteralFinding:
    """One dataset-specific literal found in a scanned pack file."""

    path: Path
    line: int
    rule: str
    excerpt: str


def discover_packs(root: Path) -> list[Path]:
    """Return pack directories directly under ``root``, sorted by name."""
    return sorted(
        child
        for child in root.iterdir()
        if child.is_dir()
        and not child.name.startswith(".")
        and child.name not in _NON_PACK_DIRS
    )


def load_denylist(pack: Path) -> list[str]:
    """Return the pack's denylisted literals, or an empty list when absent."""
    path = pack / DENYLIST_FILE
    if not path.is_file():
        return []
    literals: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        literal = raw.strip()
        if literal and not literal.startswith("#"):
            literals.append(literal)
    return literals


def _is_skipped(path: Path, pack: Path) -> bool:
    """Return whether ``path`` sits under a hidden or test-data directory."""
    for part in path.relative_to(pack).parts[:-1]:
        if part.startswith(".") or part in _SKIPPED_PACK_DIRS:
            return True
    return path.name.startswith(".")


def iter_scanned_files(pack: Path) -> Iterator[Path]:
    """Yield the pack files whose text is checked for leaked literals."""
    agent = pack / "AGENT.md"
    if agent.is_file():
        yield agent
    experts = pack / "experts"
    if experts.is_dir():
        yield from sorted(p for p in experts.glob("*.md") if p.is_file())
    skills = pack / "skills"
    if skills.is_dir():
        for path in sorted(skills.rglob("*")):
            if path.is_file() and not _is_skipped(path, pack):
                yield path


def _read_text(path: Path) -> str | None:
    """Return a file's text, or ``None`` for binary content."""
    data = path.read_bytes()
    if b"\0" in data[:_BINARY_PROBE_BYTES]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _body_start(lines: Sequence[str]) -> int:
    """Return the first line index after YAML frontmatter (0 when absent)."""
    if not lines or lines[0].strip() != "---":
        return 0
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return index + 1
    return 0


def _strict_hits(line: str) -> Iterator[tuple[str, str]]:
    """Yield ``(rule, matched_text)`` for each generic strict-rule hit."""
    for match in _ISO_DATE.finditer(line):
        yield "iso-date", match.group(0)
    for match in _MAGNITUDE.finditer(line):
        yield "measured-magnitude", match.group(0).strip()
    for match in _SAMPLE_KEY.finditer(line):
        yield "sample-key", match.group(0)
    for match in _DATA_FILE.finditer(line):
        name = match.group(0)
        basename = name.rsplit("/", 1)[-1]
        stem = basename.rsplit(".", 1)[0]
        if _TEMPLATE_CHARS.intersection(basename) or not any(c.isdigit() for c in stem):
            continue
        yield "dataset-file", basename


def scan_pack(pack: Path, *, strict: bool) -> list[LiteralFinding]:
    """Return literal findings for one pack."""
    denylist = load_denylist(pack)
    findings: list[LiteralFinding] = []
    for path in iter_scanned_files(pack):
        text = _read_text(path)
        if text is None:
            continue
        lines = text.splitlines()
        start = _body_start(lines) if path == pack / "AGENT.md" else 0
        for index in range(start, len(lines)):
            line = lines[index]
            if ALLOW_MARKER in line:
                continue
            hits: list[tuple[str, str]] = [
                ("denylist", literal) for literal in denylist if literal in line
            ]
            if strict:
                hits.extend(_strict_hits(line))
            for rule, matched in hits:
                findings.append(
                    LiteralFinding(
                        path=path, line=index + 1, rule=rule, excerpt=matched
                    )
                )
    return findings


def find_literals(
    root: Path, strict_packs: Sequence[str] = (), *, strict_all: bool = False
) -> list[LiteralFinding]:
    """Scan every pack under ``root``; strict rules apply only where opted in."""
    forced = set(strict_packs)
    findings: list[LiteralFinding] = []
    for pack in discover_packs(root):
        strict = strict_all or pack.name in forced or (pack / STRICT_MARKER).is_file()
        findings.extend(scan_pack(pack, strict=strict))
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    """Run the skill-literal check and return a process exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument(
        "--strict-pack",
        action="append",
        default=[],
        metavar="NAME",
        help="also apply the generic strict rules to this pack (repeatable)",
    )
    parser.add_argument(
        "--strict-all",
        action="store_true",
        help="apply the generic strict rules to every pack",
    )
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        # Excerpts can hold non-ASCII (e.g. "×"); never crash on a narrow console.
        sys.stdout.reconfigure(errors="backslashreplace")
    root = args.root.resolve()
    known = {pack.name for pack in discover_packs(root)}
    unknown = sorted(set(args.strict_pack) - known)
    if unknown:
        parser.error(f"unknown pack(s) for --strict-pack: {', '.join(unknown)}")
    findings = find_literals(root, args.strict_pack, strict_all=args.strict_all)
    if not findings:
        print("OK: no dataset-specific literals in marketplace pack prompts")
        return 0
    print("Dataset-specific literals in marketplace pack prompts:")
    for finding in findings:
        print(
            f"  {finding.path.relative_to(root).as_posix()}:{finding.line}: "
            f"{finding.rule}: {finding.excerpt}"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
