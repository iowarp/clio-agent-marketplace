"""Find the Chromium CLIO's browser already installed, so nothing downloads another.

    find_chromium.py

Prints JSON: ``found``, ``path`` (the executable), ``playwright`` (the Playwright release
it belongs to) and ``checked`` (the cache folders looked in). CLIO keeps Playwright's
Chromium under ``<cache>/browser/playwright-<version>/chromium-<revision>/``; the cache
is ``CLIO_AGENT_CACHE_DIR``, else ``CLIO_AGENT_HOME/cache``, else the platform default.
A shell may see ``LOCALAPPDATA`` and ``XDG_CACHE_HOME`` pointed at its workspace, so the
defaults are also derived from the home folder. Standard library only.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP = "clio-agent"
EXECUTABLES = ("chrome.exe", "chrome", "Google Chrome for Testing", "Chromium")


def cache_roots() -> list[Path]:
    roots: list[Path] = []
    if os.environ.get("CLIO_AGENT_CACHE_DIR"):
        roots.append(Path(os.environ["CLIO_AGENT_CACHE_DIR"]))
    if os.environ.get("CLIO_AGENT_HOME"):
        roots.append(Path(os.environ["CLIO_AGENT_HOME"]) / "cache")
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    if sys.platform == "win32":
        if os.environ.get("LOCALAPPDATA"):
            roots.append(Path(os.environ["LOCALAPPDATA"]) / APP / "cache")
        roots.append(home / "AppData" / "Local" / APP / "cache")
    elif sys.platform == "darwin":
        roots.append(home / "Library" / "Caches" / APP)
    else:
        if os.environ.get("XDG_CACHE_HOME"):
            roots.append(Path(os.environ["XDG_CACHE_HOME"]) / APP)
        roots.append(home / ".cache" / APP)
    unique: list[Path] = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return unique


def _version_key(folder: Path) -> tuple[int, ...]:
    tail = folder.name.split("-", 1)[-1]
    return tuple(int(p) if p.isdigit() else 0 for p in tail.split("."))


def find() -> dict[str, object]:
    checked = cache_roots()
    for root in checked:
        browsers = root / "browser"
        if not browsers.is_dir():
            continue
        for release in sorted(browsers.glob("playwright-*"), key=_version_key, reverse=True):
            for build in sorted(release.glob("chromium-*"), key=_version_key, reverse=True):
                if not (build / "INSTALLATION_COMPLETE").exists():
                    continue
                for name in EXECUTABLES:
                    for candidate in sorted(build.rglob(name)):
                        if candidate.is_file() and os.access(candidate, os.X_OK):
                            return {
                                "found": True,
                                "path": str(candidate),
                                "playwright": release.name.split("-", 1)[-1],
                                "checked": [str(c) for c in checked],
                            }
    return {"found": False, "path": "", "playwright": "", "checked": [str(c) for c in checked]}


if __name__ == "__main__":
    print(json.dumps(find(), indent=2))
