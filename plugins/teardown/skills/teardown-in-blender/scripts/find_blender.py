"""Find an installed Blender and print what was found as JSON.

    find_blender.py [--root DIR]

Looks at BLENDER (an explicit path), PATH, the usual install folders for this system,
and the user-level folder that the install-blender skill uses (``--root``, default
``~/Applications/Blender`` on macOS and ``~/.local/opt/blender`` elsewhere; on Windows
``%USERPROFILE%\\AppData\\Local\\Programs\\Blender``). Prints
``{"found": true, "path": ..., "version": ...}`` for the newest one, or ``found: false``.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def user_root() -> Path:
    home = Path.home()
    if sys.platform == "win32":
        return Path(os.environ.get("USERPROFILE") or home) / "AppData" / "Local" / "Programs" / "Blender"
    if sys.platform == "darwin":
        return home / "Applications" / "Blender"
    return home / ".local" / "opt" / "blender"


def candidates(root: Path) -> list[Path]:
    found: list[Path] = []
    if os.environ.get("BLENDER"):
        found.append(Path(os.environ["BLENDER"]))
    on_path = shutil.which("blender")
    if on_path:
        found.append(Path(on_path))
    exe = "blender.exe" if sys.platform == "win32" else "blender"
    folders: list[Path] = [root]
    if sys.platform == "win32":
        for env in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
            if os.environ.get(env):
                folders.append(Path(os.environ[env]) / "Blender Foundation")
        folders.append(Path(os.environ.get("USERPROFILE") or Path.home()) / "scoop" / "apps" / "blender" / "current")
    elif sys.platform == "darwin":
        for app in (Path("/Applications"), Path.home() / "Applications", root):
            for bundle in sorted(app.glob("Blender*.app")) if app.is_dir() else []:
                found.append(bundle / "Contents" / "MacOS" / "Blender")
    else:
        found += [Path("/usr/bin/blender"), Path("/usr/local/bin/blender"), Path("/snap/bin/blender")]
        folders.append(Path("/opt"))
    for folder in folders:
        if not folder.is_dir():
            continue
        found.append(folder / exe)
        for child in sorted(folder.iterdir(), reverse=True):
            if child.is_dir() and child.name.lower().startswith("blender"):
                found.append(child / exe)
    unique: list[Path] = []
    for path in found:
        if path.is_file() and path not in unique:
            unique.append(path)
    return unique


def version_of(path: Path) -> str | None:
    try:
        out = subprocess.run([str(path), "--version"], capture_output=True, text=True, timeout=60, check=False).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = re.search(r"Blender (\d+\.\d+(?:\.\d+)?)", out)
    return match.group(1) if match else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", help="the user-level Blender folder to look in")
    args = parser.parse_args()
    root = Path(args.root) if args.root else user_root()
    best: tuple[tuple[int, ...], Path, str] | None = None
    for path in candidates(root):
        version = version_of(path)
        if version is None:
            continue
        key = tuple(int(v) for v in version.split("."))
        if best is None or key > best[0]:
            best = (key, path, version)
    if best is None:
        print(json.dumps({"found": False, "user_root": str(root)}))
        return 1
    print(json.dumps({"found": True, "path": str(best[1]), "version": best[2], "user_root": str(root)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
