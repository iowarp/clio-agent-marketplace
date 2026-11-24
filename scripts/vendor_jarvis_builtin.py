#!/usr/bin/env python3
"""Generate or check clio-relay's copy of jarvis-cd's builtin JARVIS repository.

Relay stages packages only from its package sources, and the plugin's locked
server environment does not install jarvis-cd. So the plugin ships the builtin
repository of the jarvis-cd commit relay runs (``JARVIS_PIN``) under
``plugins/clio-relay/packages/jarvis-cd/``, and every ``builtin.<package>`` is
staged, reviewed and run like any other source package.

The copy is generated, never edited by hand:

- ``vendor_jarvis_builtin.py`` reads ``JARVIS_PIN`` from the relay wheel that
  ``plugins/clio-relay/server`` locks, downloads that jarvis-cd commit, and
  writes ``builtin/__init__.py`` and ``builtin/builtin/**``. Files larger than
  ``--max-file-bytes`` (sample and test data, not package code) are left out and
  named in the source record.
- ``vendor_jarvis_builtin.py --check`` recomputes the digest of the copy, offline,
  and fails when a file differs from what the generator wrote; ``--check --pin``
  also fails when the copy's commit is not the locked relay's ``JARVIS_PIN``.

Dependency-free; ``--commit`` skips reading the pin from the locked wheel.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from collections.abc import Iterable, Sequence
from pathlib import Path, PurePosixPath

REPOSITORY = "https://github.com/grc-iit/jarvis-cd"
ARCHIVE_URL = "https://codeload.github.com/grc-iit/jarvis-cd/tar.gz/{commit}"
REPO_NAME = "builtin"
SOURCE_FILE = ".clio-relay-source.json"
TARGET = Path("plugins/clio-relay/packages/jarvis-cd")
SERVER = Path("plugins/clio-relay/server")
GENERATOR = "scripts/vendor_jarvis_builtin.py"
DEFAULT_MAX_FILE_BYTES = 512 * 1024
_SKIP_PARTS = frozenset({"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})
_SKIP_SUFFIXES = (".pyc", ".pyo")
_LOCKED_WHEEL = re.compile(
    r'\{ url = "(?P<url>[^"]+/clio_relay-[^"/]+\.whl)", hash = "sha256:(?P<hash>[0-9a-f]{64})"'
)
_JARVIS_PIN = re.compile(r'^JARVIS_PIN\s*=\s*"([0-9a-f]{40})"', re.MULTILINE)


def _portable(data: bytes) -> bytes:
    """Return text with LF line ends, as relay archives it, so a checkout's ends never count."""
    if b"\0" in data:
        return data
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    return data.replace(b"\r\n", b"\n")


def tree_digest(files: Iterable[tuple[str, bytes]]) -> str:
    """Return the SHA-256 over each file's path and portable bytes, in path order."""
    digest = hashlib.sha256()
    for path, data in sorted(files):
        body = _portable(data)
        digest.update(f"{path}\0{len(body)}\0".encode())
        digest.update(body)
    return digest.hexdigest()


def _kept(path: PurePosixPath) -> bool:
    if not path.parts or path.parts[0] != REPO_NAME:
        return False
    if any(part in _SKIP_PARTS for part in path.parts) or path.name.endswith(
        _SKIP_SUFFIXES
    ):
        return False
    return path == PurePosixPath(REPO_NAME, "__init__.py") or (
        len(path.parts) > 2 and path.parts[1] == REPO_NAME
    )


def locked_pin(root: Path) -> str:
    """Return ``JARVIS_PIN`` from the clio-relay wheel the plugin's server project locks.

    The wheel is downloaded from the URL ``server/uv.lock`` names and checked against
    its locked hash; ``jarvis_submit.py`` is read from it, never imported.
    """
    lock = (root / SERVER / "uv.lock").read_text(encoding="utf-8")
    found = _LOCKED_WHEEL.search(lock)
    if found is None:
        raise SystemExit(f"{SERVER / 'uv.lock'} locks no clio-relay wheel with a hash")
    url, expected = found.group("url"), found.group("hash")
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit(f"{url} does not match the sha256 {SERVER / 'uv.lock'} locks")
    with zipfile.ZipFile(io.BytesIO(data)) as wheel:
        source = wheel.read("clio_relay/jarvis_submit.py").decode("utf-8")
    pin = _JARVIS_PIN.search(source)
    if pin is None:
        raise SystemExit(f"{url} sets no JARVIS_PIN in clio_relay/jarvis_submit.py")
    return pin.group(1)


def fetch(commit: str) -> dict[str, bytes]:
    """Return every file of jarvis-cd's ``builtin/`` at ``commit``, keyed by repository path."""
    with urllib.request.urlopen(
        ARCHIVE_URL.format(commit=commit), timeout=120
    ) as response:
        data = response.read()
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            parts = PurePosixPath(member.name).parts[1:]
            path = PurePosixPath(*parts) if parts else PurePosixPath()
            if not _kept(path):
                continue
            handle = tar.extractfile(member)
            if handle is not None:
                files[path.as_posix()] = handle.read()
    if f"{REPO_NAME}/__init__.py" not in files:
        raise SystemExit(f"jarvis-cd {commit} has no {REPO_NAME}/__init__.py")
    return files


def write(root: Path, commit: str, max_file_bytes: int) -> dict[str, object]:
    """Replace the copy with jarvis-cd's builtin repository at ``commit``; return its record."""
    files = fetch(commit)
    kept = {path: data for path, data in files.items() if len(data) <= max_file_bytes}
    left_out = sorted(path for path in files if path not in kept)
    target = root / TARGET
    if target.exists():
        shutil.rmtree(target)
    for path, data in kept.items():
        destination = target / PurePosixPath(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(_portable(data))
    record: dict[str, object] = {
        "commit": commit,
        "excluded": left_out,
        "generator": GENERATOR,
        "max_file_bytes": max_file_bytes,
        "path": REPO_NAME,
        "repository": REPOSITORY,
        "tree_sha256": tree_digest(kept.items()),
    }
    (target / SOURCE_FILE).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n"
    )
    return record


def _present(target: Path) -> list[tuple[str, bytes]]:
    found: list[tuple[str, bytes]] = []
    for path in sorted((target / REPO_NAME).rglob("*")):
        relative = PurePosixPath(*path.relative_to(target).parts)
        if path.is_file() and _kept(relative):
            found.append((relative.as_posix(), path.read_bytes()))
    return found


def check(root: Path, *, pin: bool = False) -> list[str]:
    """Return why the copy differs from what the generator wrote; empty when it matches.

    With ``pin``, also require its commit to be the locked relay's ``JARVIS_PIN``
    (downloads the locked wheel).
    """
    target = root / TARGET
    try:
        record = json.loads((target / SOURCE_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"{TARGET / SOURCE_FILE} is missing or unreadable: {error}"]
    problems: list[str] = []
    commit = record.get("commit") if isinstance(record, dict) else None
    if not isinstance(commit, str) or len(commit) != 40:
        problems.append(
            f"{TARGET / SOURCE_FILE} names no 40-character jarvis-cd commit"
        )
    if not isinstance(record, dict) or record.get("generator") != GENERATOR:
        problems.append(f"{TARGET / SOURCE_FILE} was not written by {GENERATOR}")
    elif record.get("tree_sha256") != tree_digest(_present(target)):
        problems.append(
            f"{TARGET} differs from jarvis-cd {str(commit)[:12]} as {GENERATOR} wrote it; "
            f"rerun {GENERATOR} rather than editing the copy"
        )
    if pin and isinstance(commit, str) and commit != (locked := locked_pin(root)):
        problems.append(
            f"{TARGET} is jarvis-cd {commit[:12]}, but the locked relay runs {locked[:12]} "
            f"(JARVIS_PIN); rerun {GENERATOR}"
        )
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    parser.add_argument(
        "--commit", help="jarvis-cd commit; default: the locked relay's JARVIS_PIN"
    )
    parser.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    parser.add_argument("--check", action="store_true", help="verify the copy, offline")
    parser.add_argument(
        "--pin",
        action="store_true",
        help="with --check, also match the locked JARVIS_PIN",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.check:
        problems = check(root, pin=args.pin)
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1 if problems else 0
    commit = args.commit or locked_pin(root)
    record = write(root, commit, args.max_file_bytes)
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
