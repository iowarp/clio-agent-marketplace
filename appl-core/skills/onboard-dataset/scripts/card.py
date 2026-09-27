# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Create, check, and fingerprint the experiment card for one dataset.

Per-dataset (L3) artefacts live in the ACTIVE WORKSPACE, never in the data
folder. The raw export is read-only input (it may be a shared or read-only
facility mount); ``--store`` names the workspace root (default: the current
working directory, which in clio is the session workspace). Each dataset gets
its own directory there::

    <store>/.clio/datasets/<key>/
        experiment-card.md   # facts, traps, open questions, loader/view hashes
        loader.py            # reads BUNDLE_ROOT, writes ./views/
        views/               # validated tables written by the loader
        audit/               # JSON reports from the audit scripts (--out)

``<key>`` is the first 16 hex characters of the SHA-256 of the bundle's
manifest file (``manifest.json``), so a second session -- or the same export
mounted at a different path -- finds the same card. Without a manifest the key
falls back to the SHA-256 of the resolved absolute bundle path (after
``os.path.normcase``); that key changes when the data moves. The card's
frontmatter records the absolute bundle path, the manifest SHA-256, and the
export version.

Commands::

    python card.py status BUNDLE_ROOT [--store WS]  # dataset dir, card present? current?
    python card.py init   BUNDLE_ROOT [--store WS] [--force]  # write a card from the template
    python card.py record BUNDLE_ROOT [--store WS]  # store loader + view hashes in the card
    python card.py verify BUNDLE_ROOT [--store WS]  # exit 1 unless the card is current and
                                                    # loader/views match the recorded hashes

Only the dataset directory under the store is ever written; the bundle root is
never modified, and a store that would put the dataset directory inside the
bundle root is refused. Uses the standard library only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

CARD_FORMAT = "clio-experiment-card/1"
STORE_DIR = ".clio"
DATASETS_DIR = "datasets"
KEY_LENGTH = 16
CARD_NAME = "experiment-card.md"
LOADER_NAME = "loader.py"
VIEWS_DIR = "views"
AUDIT_DIR = "audit"
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
dataset_key: {dataset_key}
key_source: {key_source}
bundle_root: {bundle_root}
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

- [checked] bundle root when the card was created: `{bundle_root}` (read-only input)
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

The loader is `{loader}` next to this card. Run it as
`uv run --no-project {loader} BUNDLE_ROOT`: it reads the raw files from
BUNDLE_ROOT (never writing there), applies the decisions above, and writes
validated views under `{views}/` next to this card. Paths below are relative
to this card's directory. `card.py record` fills the block; `card.py verify`
re-checks it.

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


def dataset_key(root: Path) -> tuple[str, str]:
    """The dataset's store key and its source (``"manifest"`` or ``"path"``).

    With a manifest: the first 16 hex chars of the manifest file's SHA-256, so
    the same export at any path maps to the same key. Without one: the first 16
    hex chars of the SHA-256 of the resolved absolute bundle path (normalised
    with ``os.path.normcase``), which changes if the data moves.
    """

    manifest = find_manifest(root)
    if manifest is not None:
        return _sha256(manifest)[:KEY_LENGTH], "manifest"
    resolved = os.path.normcase(str(root.resolve()))
    return hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:KEY_LENGTH], "path"


def datasets_root(store: Path) -> Path:
    """``<store>/.clio/datasets``: the parent of every dataset directory."""

    return store / STORE_DIR / DATASETS_DIR


def dataset_dir(root: Path, store: Path) -> Path:
    """Absolute ``<store>/.clio/datasets/<key>/`` for the bundle at ``root``."""

    key, _ = dataset_key(root)
    return (datasets_root(store) / key).resolve()


def check_store(root: Path, store: Path) -> str | None:
    """A reason to refuse ``store`` (dataset dir inside the bundle), or None."""

    if dataset_dir(root, store).is_relative_to(root.resolve()):
        return (
            f"store {store} would put the dataset directory inside the bundle root "
            f"{root}; the raw export is read-only input. Pass the active workspace "
            "root as --store."
        )
    return None


def _paths(directory: Path) -> tuple[Path, Path, Path]:
    return directory / CARD_NAME, directory / LOADER_NAME, directory / VIEWS_DIR


def current_hashes(directory: Path) -> dict[str, Any]:
    """SHA-256 of the saved loader and of every view file in a dataset directory.

    Paths are relative to the dataset directory, so the record does not depend
    on where the workspace lives.
    """

    _, loader, views = _paths(directory)
    return {
        "loader": LOADER_NAME,
        "loader_sha256": _sha256(loader) if loader.is_file() else None,
        "views": {
            path.relative_to(directory).as_posix(): _sha256(path)
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


def init(root: Path, store: Path, *, force: bool = False) -> dict[str, Any]:
    """Write a fresh card under the store (refuses to overwrite without force)."""

    refusal = check_store(root, store)
    if refusal is not None:
        return {"ok": False, "reason": refusal}
    directory = dataset_dir(root, store)
    card, _, _ = _paths(directory)
    if card.exists() and not force:
        return {
            "ok": False,
            "card": str(card),
            "reason": "card exists; use status, or --force to replace it",
        }
    identity = manifest_identity(root)
    key, source = dataset_key(root)
    text = TEMPLATE.format(
        card_format=CARD_FORMAT,
        dataset_key=key,
        key_source=source,
        bundle_root=root.resolve(),
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
        loader=LOADER_NAME,
        views=VIEWS_DIR,
        hashes=json.dumps(
            {"loader": LOADER_NAME, "loader_sha256": None, "views": {}}, indent=2
        ),
    )
    directory.mkdir(parents=True, exist_ok=True)
    card.write_text(text, encoding="utf-8", newline="\n")
    return {
        "ok": True,
        "dataset_dir": str(directory),
        "card": str(card),
        "dataset_key": key,
        "key_source": source,
        **identity,
    }


def _cards_for_bundle(root: Path, store: Path, skip: Path) -> list[str]:
    """Cards in the store (other than the one in ``skip``) made for this bundle path."""

    base = datasets_root(store)
    if not base.is_dir():
        return []
    wanted = os.path.normcase(str(root.resolve()))
    found = []
    for card in sorted(base.glob(f"*/{CARD_NAME}")):
        if card.parent.resolve() == skip:
            continue
        try:
            meta = parse_frontmatter(card.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        recorded = meta.get("bundle_root")
        if recorded and os.path.normcase(recorded) == wanted:
            found.append(str(card))
    return found


def status(root: Path, store: Path) -> dict[str, Any]:
    """Where the dataset directory is, whether its card is current, and hash drift.

    ``state`` is ``current`` (a card for this manifest), ``no_manifest`` (a card
    keyed by path; nothing to compare), ``stale`` (no card for this manifest,
    but the store holds a card made for this bundle path from a different
    manifest: the export changed), or ``no_card``.
    """

    directory = dataset_dir(root, store)
    card, loader, views = _paths(directory)
    identity = manifest_identity(root)
    key, source = dataset_key(root)
    report: dict[str, Any] = {
        "store": str(store.resolve()),
        "dataset_key": key,
        "key_source": source,
        "dataset_dir": str(directory),
        "dataset_dir_exists": directory.is_dir(),
        "card": str(card),
        "card_exists": card.is_file(),
        "loader": str(loader),
        "loader_exists": loader.is_file(),
        "views_dir": str(views),
        "views_exist": views.is_dir() and any(p.is_file() for p in views.rglob("*")),
        "audit_dir": str(directory / AUDIT_DIR),
        "current_manifest_sha256": identity["manifest_sha256"],
    }
    if not card.is_file():
        previous = _cards_for_bundle(root, store, directory)
        if previous:
            report["state"] = "stale"
            report["previous_cards"] = previous
        else:
            report["state"] = "no_card"
        return report
    text = card.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    report["card_manifest_sha256"] = meta.get("manifest_sha256")
    report["manifest_match"] = (
        identity["manifest_sha256"] is not None
        and meta.get("manifest_sha256") == identity["manifest_sha256"]
    )
    report["card_bundle_root"] = meta.get("bundle_root")
    report["card_status"] = meta.get("status")
    report["card_export_version"] = meta.get("export_version")
    if identity["manifest_sha256"] is None:
        report["state"] = "no_manifest"
    elif report["manifest_match"]:
        report["state"] = "current"
    else:
        report["state"] = "stale"
    recorded = recorded_hashes(text)
    now = current_hashes(directory)
    if recorded is None or (
        recorded.get("loader_sha256") is None and not recorded.get("views")
    ):
        report["hashes"] = "not_recorded"
    else:
        drift = []
        if recorded.get("loader_sha256") != now["loader_sha256"]:
            drift.append(recorded.get("loader", LOADER_NAME))
        rec_views = recorded.get("views") or {}
        for path in sorted(set(rec_views) | set(now["views"])):
            if rec_views.get(path) != now["views"].get(path):
                drift.append(path)
        report["hashes"] = "match" if not drift else "drift"
        report["drifted"] = drift
    return report


def record(root: Path, store: Path) -> dict[str, Any]:
    """Store the current loader and view hashes in the card's hash block."""

    directory = dataset_dir(root, store)
    card, _, _ = _paths(directory)
    if not card.is_file():
        return {"ok": False, "card": str(card), "reason": "no card; run init first"}
    text = card.read_text(encoding="utf-8").replace("\r\n", "\n")
    hashes = current_hashes(directory)
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
        "--store",
        type=Path,
        default=None,
        help=(
            "workspace root that holds .clio/datasets/<key>/ (pass the active "
            "workspace root; default: the current working directory)"
        ),
    )
    parser.add_argument(
        "--force", action="store_true", help="init: replace an existing card"
    )
    args = parser.parse_args(argv)
    root = args.bundle_root
    store = args.store if args.store is not None else Path.cwd()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    if args.command == "init":
        report = init(root, store, force=args.force)
        _print(report)
        return 0 if report["ok"] else 1
    refusal = check_store(root, store)
    if refusal is not None:
        print(f"error: {refusal}", file=sys.stderr)
        return 2
    if args.command == "record":
        report = record(root, store)
        _print(report)
        return 0 if report["ok"] else 1
    report = status(root, store)
    _print(report)
    if args.command == "verify":
        fresh = report.get("state") in {"current", "no_manifest"}
        return 0 if fresh and report.get("hashes") == "match" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
