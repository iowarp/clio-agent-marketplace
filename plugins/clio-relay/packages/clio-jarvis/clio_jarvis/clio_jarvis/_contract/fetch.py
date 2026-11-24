"""A package's public input, fetched on the site by the package itself.

A guarded site runs reviewed packages only, so the agent cannot download a
case there with a command of its own, and carrying gigabytes through the
person's computer is slow. A package whose parameters name an archive URL
fetches it inside its job: :func:`fetch_archive` streams the archive once,
hashes it as it reads, extracts only the members the package wants into a
staging directory beside the destination, and renames that into place when
every required file arrived. A half-done fetch never looks like a case.

One fetch per destination runs at a time. The lock is a directory holding
``owner.json``; the running fetch touches it as bytes arrive, so a lock left
by a killed job is stale after :data:`STALE_SECONDS` and the next fetch takes
it over.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import shutil
import socket
import tarfile
import time
import urllib.request
from collections.abc import Callable, Iterable
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO

SOURCE_NAME = "clio-input-source.json"
STALE_SECONDS = 600.0
CHUNK = 1 << 20
_TOUCH_BYTES = 64 << 20


class _Hashing:
    """A read-only stream that hashes and counts what passes through it."""

    def __init__(self, inner: BinaryIO, digest: Any, touch: Callable[[], None]) -> None:
        self.inner, self.digest, self.touch = inner, digest, touch
        self.count = 0
        self._since_touch = 0

    def read(self, size: int = -1) -> bytes:
        data = self.inner.read(size)
        self.digest.update(data)
        self.count += len(data)
        self._since_touch += len(data)
        if self._since_touch >= _TOUCH_BYTES:
            self._since_touch = 0
            self.touch()
        return data


def _take_lock(lock: Path) -> None:
    owner = {"host": socket.gethostname(), "pid": os.getpid(), "at": time.time()}
    for _ in range(2):
        try:
            lock.mkdir()
        except FileExistsError:
            try:
                age = time.time() - lock.stat().st_mtime
            except FileNotFoundError:
                continue
            if age < STALE_SECONDS:
                held = (lock / "owner.json").read_text(encoding="utf-8", errors="replace") if (lock / "owner.json").is_file() else "unknown"
                raise RuntimeError(f"another fetch of this input runs ({held}); it is stale after {int(STALE_SECONDS)} s without progress") from None
            shutil.rmtree(lock, ignore_errors=True)
            continue
        (lock / "owner.json").write_text(json.dumps(owner) + "\n", encoding="utf-8")
        return
    raise RuntimeError(f"could not take the fetch lock {lock}")


def fetch_archive(
    url: str,
    dest: Path,
    *,
    want: Callable[[str], bool],
    required: Iterable[str],
    sha256: str = "",
    timeout: float = 120.0,
    say: Callable[[str], None] = lambda line: print(line, flush=True),
) -> dict[str, Any]:
    """Fetch the tar archive at ``url`` and place the members ``want`` names in ``dest``.

    Members are matched and placed by their base name; two members with one
    base name are refused rather than guessed. ``required`` names the files
    the destination must end up with. With ``sha256``, the archive must have
    that digest. ``dest`` must be absent or empty. Returns the source record,
    also written to ``dest / SOURCE_NAME``.
    """
    if not url.startswith("https://"):
        raise ValueError(f"an input archive URL must be https: {url}")
    dest = Path(dest)
    if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
        raise ValueError(f"{dest} already exists without the input's files; empty it or name another directory")
    dest.parent.mkdir(parents=True, exist_ok=True)
    lock = dest.parent / f".{dest.name}.fetch-lock"
    _take_lock(lock)
    staging = dest.parent / f".{dest.name}.fetch-{socket.gethostname()}-{os.getpid()}"

    def touch() -> None:
        try:
            os.utime(lock)
        except OSError:
            pass

    try:
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir()
        digest = hashlib.sha256()
        files: dict[str, dict[str, Any]] = {}
        say(f"clio-fetch {url}")
        started = time.monotonic()
        with urllib.request.urlopen(url, timeout=timeout) as response:
            stream = _Hashing(response, digest, touch)
            with tarfile.open(fileobj=stream, mode="r|*") as archive:  # type: ignore[call-overload]
                for member in archive:
                    name = PurePosixPath(member.name).name
                    if not member.isfile() or not want(name):
                        continue
                    if name in files:
                        raise ValueError(f"the archive holds {name} twice ({files[name]['member']} and {member.name})")
                    source = archive.extractfile(member)
                    if source is None:
                        continue
                    with source, (staging / name).open("xb") as out:
                        shutil.copyfileobj(source, out, CHUNK)
                    if (staging / name).stat().st_size != member.size:
                        raise ValueError(f"{name} arrived with {(staging / name).stat().st_size} bytes of {member.size}")
                    files[name] = {"member": member.name, "bytes": member.size}
                    say(f"clio-fetch {name} {member.size} bytes")
            while stream.read(CHUNK):
                pass
        missing = [name for name in required if name not in files]
        if missing:
            raise ValueError(f"{url} holds no {', '.join(missing)}")
        actual = digest.hexdigest()
        if sha256 and actual != sha256.strip().lower():
            raise ValueError(f"{url} has sha256 {actual}, not the expected {sha256}")
        record = {
            "url": url,
            "sha256": actual,
            "bytes": stream.count,
            "seconds": round(time.monotonic() - started, 1),
            "files": files,
            "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "host": socket.gethostname(),
        }
        (staging / SOURCE_NAME).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        if dest.exists():
            dest.rmdir()
        staging.rename(dest)
        say(f"clio-fetch done {stream.count} bytes in {record['seconds']} s, sha256 {actual}")
        return record
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(lock, ignore_errors=True)
