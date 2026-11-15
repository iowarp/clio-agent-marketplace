#!/usr/bin/env python3
"""Reproduce the vendored Home Assistant skill from a reviewed Git revision.

The ``home-assistant`` plugin ships ``home-assistant-best-practices`` from
homeassistant-ai/skills (MIT) unchanged, with its licence beside it. This script
copies the skill folder from ``REVISION`` and records every file's sha256 in
``plugins/home-assistant/import-lock.json``. An existing copy is replaced only if
every file still matches the lock, so a local change needs a deliberate review
(edit the lock by hand, or delete the folder) instead of being overwritten.

    python scripts/import_home_assistant_skills.py            # re-import REVISION
    python scripts/import_home_assistant_skills.py --check    # verify the lock only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/homeassistant-ai/skills"
REVISION = "166defa51c606b3c77d45a9b29a459d1f993f357"
SKILL = "home-assistant-best-practices"
PLUGIN = ROOT / "plugins" / "home-assistant"
DESTINATION = PLUGIN / "skills" / SKILL
LOCK = PLUGIN / "import-lock.json"
LICENSE_NAME = "LICENSE.txt"


def digests(folder: Path) -> dict[str, str]:
    """``{relative path: sha256}`` of every file under ``folder``."""
    return {
        path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def check() -> list[str]:
    """The differences between the vendored files and the lock ([] when equal)."""
    if not LOCK.is_file():
        return [f"{LOCK.relative_to(ROOT)} is missing"]
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    recorded = dict(lock.get("files") or {})
    present = digests(DESTINATION) if DESTINATION.is_dir() else {}
    problems = [f"changed: {name}" for name in recorded if present.get(name) not in (None, recorded[name])]
    problems += [f"missing: {name}" for name in recorded if name not in present]
    problems += [f"not in the lock: {name}" for name in present if name not in recorded]
    return problems


def fetch(work: Path) -> Path:
    """Clone ``REPOSITORY`` at ``REVISION`` into ``work``; return the checkout."""
    checkout = work / "skills"
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    subprocess.run(["git", "-C", str(checkout), "remote", "add", "origin", REPOSITORY], check=True)
    subprocess.run(
        ["git", "-C", str(checkout), "fetch", "-q", "--depth", "1", "origin", REVISION], check=True
    )
    subprocess.run(["git", "-C", str(checkout), "checkout", "-q", "FETCH_HEAD"], check=True)
    return checkout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify the lock; change nothing")
    args = parser.parse_args(argv)
    if args.check or DESTINATION.is_dir():
        problems = check() if LOCK.is_file() or DESTINATION.is_dir() else []
        if args.check:
            print("\n".join(problems) or "home-assistant skill matches its lock")
            return 1 if problems else 0
        if problems:
            print("refusing to replace a vendored skill that differs from its lock:", file=sys.stderr)
            print("\n".join(problems), file=sys.stderr)
            return 1
    with tempfile.TemporaryDirectory() as tmp:
        checkout = fetch(Path(tmp))
        if DESTINATION.exists():
            shutil.rmtree(DESTINATION)
        shutil.copytree(checkout / "skills" / SKILL, DESTINATION)
        shutil.copyfile(checkout / "LICENSE", DESTINATION / LICENSE_NAME)
    lock = {
        "schema": 1,
        "repository": REPOSITORY,
        "revision": REVISION,
        "path": f"skills/{SKILL}",
        "license": "MIT",
        "license_file": LICENSE_NAME,
        "adaptations": [f"Added the upstream LICENSE as {LICENSE_NAME}; no file changed"],
        "files": digests(DESTINATION),
    }
    LOCK.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(f"imported {SKILL} at {REVISION[:12]} ({len(lock['files'])} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
