# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Create, check, and fingerprint the experiment card that lives with a dataset.

The card is ``<bundle_root>/.clio/experiment-card.md``. It is keyed by the
SHA-256 of the bundle's ``manifest.json`` (plus ``export_version`` and
``generated_at`` when the manifest declares them), so a later session can tell
whether the card still describes the files on disk.

Commands::

    python card.py init   BUNDLE_ROOT [--force]  # write a card from the template
    python card.py status BUNDLE_ROOT            # card present? manifest hash still matches?
    python card.py record BUNDLE_ROOT            # store loader + view hashes in the card
    python card.py verify BUNDLE_ROOT            # exit 1 unless the card is current and
                                                 # loader/views match the recorded hashes

Only ``.clio/`` is ever written; the dataset itself is never modified. Uses the
standard library only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

CARD_FORMAT = "clio-experiment-card/1"
AGENT_DIR = ".clio"
CARD_NAME = "experiment-card.md"
LOADER_NAME = "loader.py"
VIEWS_DIR = "views"
MANIFEST_NAMES = ("manifest.json", "MANIFEST.json")

#: Shared vocabulary for tagging traps in the card (``- [trap:<class>] ...``).
#: Graders read these tags, so keep the names stable.
TRAP_CLASSES: dict[str, str] = {
    "sentinel-values": "a numeric code (float max, -9999, ...) stands for missing",
    "ghost-columns": "all-empty or string-typed-but-empty columns, often twins of real ones",
    "near-duplicate-columns": "names differing only by rounding/case; duplicate-content columns",
    "unflagged-missing": "rows with no signal that the QC flags do not mark",
    "universal-flag": "a flag set on (almost) every row, so it filters nothing",
    "key-format-mismatch": "join keys differ in format/case/type between tables",
    "declared-vs-actual": "manifest/docs/QC tables disagree with the files (counts, missing tables, empty issue logs)",
    "unit-scale-suspect": "a unit or scale that is physically implausible or disagrees with another instrument",
    "saturation-clipping": "a growth-like signal plateaus because of the measurement, not the biology",
    "irregular-sampling": "gaps, split/aborted rounds, several observations per unit per period",
    "design-encoding": "design unbalanced, factors duplicated, dose vs category ambiguity",
    "duplicate-measures": "the same quantity from two sources/methods that disagree",
    "impossible-values": "zeros, negatives, or extremes that cannot be physical",
    "list-in-string": "lists or JSON stored inside string cells",
    "label-inconsistency": "misspelled or inconsistent labels for the same entity",
}

TEMPLATE = """---
card_format: {card_format}
manifest: {manifest}
manifest_sha256: {manifest_sha256}
export_version: {export_version}
generated_at: {generated_at}
card_created: {created}
status: draft
---

# Experiment card

Facts about this one dataset. Tag every line: `[stated]` (the export says so;
cite the file), `[checked]` (verified in the data; cite the command or
script output), `[inferred]` (an interpretation; list it under open questions
until the data owners confirm it). Never copy a fact from another dataset's card.

## Identity

- [checked] manifest `{manifest}` sha256 `{manifest_sha256}`
- [stated] export_version: {export_version}
- [stated] generated_at: {generated_at}

## Stated facts

<!-- - [stated] <fact> (source: <file and section>) -->

## Checked facts

<!-- - [checked] <fact> (evidence: <script/command and the number it printed>) -->

## Inferred facts

<!-- - [inferred] <interpretation> (why: <evidence>; confirm with: <who>) -->

## Traps found

<!-- One line per trap:
- [trap:<class>] <table/column> -- <what is wrong> -- <how the loader handles it> (evidence: <...>)
Classes: {trap_classes}
-->

## Open questions for data owners

<!-- - <question> (why it matters: <which analysis changes with the answer>) -->

## Proposed lessons

<!-- Phrase each as a check that would apply to ANY dataset, not a fact about this one:
- check: <"check whether ..."> (seen here; promote only after another export shows it)
-->

## Loader and views

The loader is `{agent_dir}/{loader}`; it reads the raw files, applies the
decisions above, and writes validated views under `{agent_dir}/{views}/`.
`card.py record` fills the block below; `card.py verify` re-checks it.

```json
{hashes}
```
"""

_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_HASH_BLOCK = re.compile(r"(## Loader and views.*?```json\n)(.*?)(\n```)", re.DOTALL)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def find_manifest(root: Path) -> Path | None:
    """The bundle's manifest file, if it has one."""

    return next(
        (root / name for name in MANIFEST_NAMES if (root / name).is_file()), None
    )


def manifest_identity(root: Path) -> dict[str, Any]:
    """Identity keys of the bundle: manifest path, sha256, export_version, generated_at."""

    manifest = find_manifest(root)
    if manifest is None:
        return {
            "manifest": None,
            "manifest_sha256": None,
            "export_version": None,
            "generated_at": None,
        }
    identity: dict[str, Any] = {
        "manifest": manifest.name,
        "manifest_sha256": _sha256(manifest),
        "export_version": None,
        "generated_at": None,
    }
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return identity
    if isinstance(data, dict):
        for key in ("export_version", "generated_at"):
            value = data.get(key)
            if value is not None and not isinstance(value, (dict, list)):
                identity[key] = value
    return identity


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the card's flat ``key: value`` frontmatter."""

    match = _FRONTMATTER.match(text.replace("\r\n", "\n"))
    if not match:
        return {}
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip()
    return meta


def _paths(root: Path) -> tuple[Path, Path, Path]:
    agent = root / AGENT_DIR
    return agent / CARD_NAME, agent / LOADER_NAME, agent / VIEWS_DIR


def current_hashes(root: Path) -> dict[str, Any]:
    """SHA-256 of the saved loader and of every file under the views directory."""

    _, loader, views = _paths(root)
    return {
        "loader": f"{AGENT_DIR}/{LOADER_NAME}",
        "loader_sha256": _sha256(loader) if loader.is_file() else None,
        "views": {
            path.relative_to(root).as_posix(): _sha256(path)
            for path in sorted(views.rglob("*"))
            if path.is_file()
        }
        if views.is_dir()
        else {},
    }


def recorded_hashes(text: str) -> dict[str, Any] | None:
    """The hashes block stored in the card, or None when absent/unparseable."""

    match = _HASH_BLOCK.search(text.replace("\r\n", "\n"))
    if not match:
        return None
    try:
        value = json.loads(match.group(2))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def init(root: Path, *, force: bool = False) -> dict[str, Any]:
    """Write a fresh card from the template (refuses to overwrite without force)."""

    card, _, _ = _paths(root)
    if card.exists() and not force:
        return {
            "ok": False,
            "card": str(card),
            "reason": "card exists; use status, or --force to replace it",
        }
    identity = manifest_identity(root)
    text = TEMPLATE.format(
        card_format=CARD_FORMAT,
        manifest=identity["manifest"] or "none",
        manifest_sha256=identity["manifest_sha256"] or "none",
        export_version=identity["export_version"]
        if identity["export_version"] is not None
        else "unknown",
        generated_at=identity["generated_at"]
        if identity["generated_at"] is not None
        else "unknown",
        created=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        trap_classes=", ".join(TRAP_CLASSES),
        agent_dir=AGENT_DIR,
        loader=LOADER_NAME,
        views=VIEWS_DIR,
        hashes=json.dumps(
            {
                "loader": f"{AGENT_DIR}/{LOADER_NAME}",
                "loader_sha256": None,
                "views": {},
            },
            indent=2,
        ),
    )
    card.parent.mkdir(parents=True, exist_ok=True)
    card.write_text(text, encoding="utf-8", newline="\n")
    return {"ok": True, "card": str(card), **identity}


def status(root: Path) -> dict[str, Any]:
    """Whether a card exists, whether it still matches the manifest, and hash drift."""

    card, loader, views = _paths(root)
    identity = manifest_identity(root)
    report: dict[str, Any] = {
        "card": str(card),
        "card_exists": card.is_file(),
        "loader_exists": loader.is_file(),
        "views_exist": views.is_dir() and any(p.is_file() for p in views.rglob("*")),
        "current_manifest_sha256": identity["manifest_sha256"],
    }
    if not card.is_file():
        report["state"] = "no_card"
        return report
    text = card.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    report["card_manifest_sha256"] = meta.get("manifest_sha256")
    report["card_status"] = meta.get("status")
    report["card_export_version"] = meta.get("export_version")
    if identity["manifest_sha256"] is None:
        report["state"] = "no_manifest"
    elif meta.get("manifest_sha256") == identity["manifest_sha256"]:
        report["state"] = "current"
    else:
        report["state"] = "stale"
    recorded = recorded_hashes(text)
    now = current_hashes(root)
    if recorded is None or (
        recorded.get("loader_sha256") is None and not recorded.get("views")
    ):
        report["hashes"] = "not_recorded"
    else:
        drift = []
        if recorded.get("loader_sha256") != now["loader_sha256"]:
            drift.append(recorded.get("loader", "loader"))
        rec_views = recorded.get("views") or {}
        for path in sorted(set(rec_views) | set(now["views"])):
            if rec_views.get(path) != now["views"].get(path):
                drift.append(path)
        report["hashes"] = "match" if not drift else "drift"
        report["drifted"] = drift
    return report


def record(root: Path) -> dict[str, Any]:
    """Store the current loader and view hashes in the card's hash block."""

    card, _, _ = _paths(root)
    if not card.is_file():
        return {"ok": False, "reason": "no card; run init first"}
    text = card.read_text(encoding="utf-8").replace("\r\n", "\n")
    hashes = current_hashes(root)
    rendered = json.dumps(hashes, indent=2)
    if _HASH_BLOCK.search(text):
        text = _HASH_BLOCK.sub(
            lambda m: m.group(1) + rendered + m.group(3), text, count=1
        )
    else:
        text = (
            text.rstrip("\n")
            + "\n\n## Loader and views\n\n```json\n"
            + rendered
            + "\n```\n"
        )
    card.write_text(text, encoding="utf-8", newline="\n")
    return {"ok": True, "card": str(card), **hashes}


def _print(report: dict[str, Any]) -> None:
    for key, value in report.items():
        if key == "views" and isinstance(value, dict):
            print(f"views: {len(value)} file(s)")
            for path, digest in list(value.items())[:20]:
                print(f"  {path} {digest}")
        else:
            print(f"{key}: {value}")
    print("--- json ---")
    print(json.dumps(report, indent=2))


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("command", choices=("init", "status", "record", "verify"))
    parser.add_argument("bundle_root", type=Path)
    parser.add_argument(
        "--force", action="store_true", help="init: replace an existing card"
    )
    args = parser.parse_args(argv)
    root = args.bundle_root
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    if args.command == "init":
        report = init(root, force=args.force)
        _print(report)
        return 0 if report["ok"] else 1
    if args.command == "record":
        report = record(root)
        _print(report)
        return 0 if report["ok"] else 1
    report = status(root)
    _print(report)
    if args.command == "verify":
        fresh = report.get("state") in {"current", "no_manifest"}
        return 0 if fresh and report.get("hashes") == "match" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
