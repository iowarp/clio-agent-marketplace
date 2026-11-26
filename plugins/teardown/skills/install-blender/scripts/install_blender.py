"""Install Blender for this user, with no admin rights, from the official release files.

    install_blender.py [--series 4.5] [--root DIR] [--dry-run]

Finds the newest point release of the series (an LTS by default) on download.blender.org
or one of Blender's official mirrors, downloads the archive for this system, checks it
against the release's published sha256, and unpacks it into a user-level folder: on
Windows ``%USERPROFILE%\\AppData\\Local\\Programs\\Blender``, on macOS
``~/Applications/Blender`` (the app copied out of the disk image), elsewhere
``~/.local/opt/blender``. ``--dry-run`` prints the plan (version, URL, sha256, size,
folder) without downloading. Prints JSON last, including the ``blender`` executable.
Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

MIRRORS = (
    "https://download.blender.org/release",
    "https://ftp.nluug.nl/pub/graphics/blender/release",
    "https://mirrors.ocf.berkeley.edu/blender/release",
    "https://mirror.clarkson.edu/blender/release",
)
AGENT = {"User-Agent": "clio-teardown-install-blender/1.0"}


def user_root() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("USERPROFILE") or Path.home()) / "AppData" / "Local" / "Programs" / "Blender"
    if sys.platform == "darwin":
        return Path.home() / "Applications" / "Blender"
    return Path.home() / ".local" / "opt" / "blender"


def archive_suffix() -> str:
    machine = platform.machine().lower()
    arm = machine in ("arm64", "aarch64")
    if sys.platform == "win32":
        if arm:
            raise SystemExit("Blender publishes only an installer for Windows on Arm; use winget (BlenderFoundation.Blender) instead")
        return "windows-x64.zip"
    if sys.platform == "darwin":
        return "macos-arm64.dmg" if arm else "macos-x64.dmg"
    if arm:
        raise SystemExit("Blender publishes no Linux Arm build; use the bpy route or a distribution package")
    return "linux-x64.tar.xz"


def fetch(url: str, timeout: float = 30.0) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=timeout) as resp:
        return resp.read()


def newest(series: str) -> tuple[str, str, str]:
    """(mirror base, version, sha256 listing) for the newest point release reachable."""
    pattern = re.compile(rf"blender-({re.escape(series)}\.\d+)\.sha256")
    errors: list[str] = []
    for base in MIRRORS:
        folder = f"{base}/Blender{series}/"
        try:
            listing = fetch(folder).decode("utf-8", "replace")
            versions = sorted(set(pattern.findall(listing)), key=lambda v: tuple(int(x) for x in v.split(".")))
            if not versions:
                errors.append(f"{folder}: no releases listed")
                continue
            version = versions[-1]
            sums = fetch(f"{folder}blender-{version}.sha256").decode("utf-8", "replace")
        except (urllib.error.URLError, OSError) as exc:
            errors.append(f"{folder}: {exc}")
            continue
        return base, version, sums
    raise SystemExit("no Blender release folder was reachable:\n  " + "\n  ".join(errors))


def expected_sha(sums: str, name: str) -> str:
    for line in sums.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == name:
            return parts[0].lower()
    raise SystemExit(f"{name} is not in the release's sha256 list")


def download(url: str, dest: Path, sha: str) -> None:
    digest = hashlib.sha256()
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=60) as resp, dest.open("wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        done, shown = 0, -1
        while chunk := resp.read(1 << 20):
            out.write(chunk)
            digest.update(chunk)
            done += len(chunk)
            if total and done * 10 // total != shown:
                shown = done * 10 // total
                print(f"downloaded {done * 100 // total}%", file=sys.stderr, flush=True)
    if digest.hexdigest() != sha:
        dest.unlink(missing_ok=True)
        raise SystemExit(f"checksum mismatch for {url}: the download was removed")


def unpack(archive: Path, root: Path, version: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zf:
            top = zf.namelist()[0].split("/")[0]
            zf.extractall(root)
        return root / top / "blender.exe"
    if archive.name.endswith(".tar.xz"):
        with tarfile.open(archive) as tf:
            top = tf.getnames()[0].split("/")[0]
            if sys.version_info >= (3, 12):
                tf.extractall(root, filter="tar")
            else:
                tf.extractall(root)
        return root / top / "blender"
    mount = Path(tempfile.mkdtemp(prefix="blender-dmg-"))
    subprocess.run(["hdiutil", "attach", "-nobrowse", "-readonly", "-mountpoint", str(mount), str(archive)], check=True, capture_output=True)
    try:
        target = root / f"Blender {version}.app"
        if target.exists():
            shutil.rmtree(target)
        subprocess.run(["ditto", str(mount / "Blender.app"), str(target)], check=True)
    finally:
        subprocess.run(["hdiutil", "detach", str(mount)], check=False, capture_output=True)
    return target / "Contents" / "MacOS" / "Blender"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--series", default="4.5", help="release series, e.g. 4.5 (LTS)")
    parser.add_argument("--root", help="user-level folder to install into")
    parser.add_argument("--dry-run", action="store_true", help="print the plan only")
    args = parser.parse_args()
    root = Path(args.root) if args.root else user_root()
    base, version, sums = newest(args.series)
    name = f"blender-{version}-{archive_suffix()}"
    sha = expected_sha(sums, name)
    url = f"{base}/Blender{args.series}/{name}"
    plan: dict[str, object] = {"version": version, "url": url, "sha256": sha, "folder": str(root)}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT, method="HEAD"), timeout=30) as head:
            plan["size_mb"] = round(int(head.headers.get("Content-Length") or 0) / 1e6)
    except (urllib.error.URLError, OSError):
        pass
    if args.dry_run:
        print(json.dumps({"dry_run": True, **plan}, indent=1))
        return 0
    with tempfile.TemporaryDirectory(prefix="blender-get-") as tmp:
        archive = Path(tmp) / name
        download(url, archive, sha)
        exe = unpack(archive, root, version)
    if not exe.is_file():
        raise SystemExit(f"unpacked, but {exe} is missing")
    out = subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=120, check=False).stdout
    print(json.dumps({"installed": True, **plan, "blender": str(exe), "reports": out.splitlines()[0] if out else ""}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
