"""Open files by handle, many at once, each owned by the session that opened it.

A plugin server serves every session of a workspace. A handle is keyed by the calling
session (CLIO names it in each call's ``_meta``), so one session cannot use or close
another's file. A file is a local path, or a byte-range URL CLIO hands out for a file in
a linked source; only URLs under the origin CLIO configures (``CLIO_SOURCE_RANGE_ORIGIN``)
are opened, so the server never fetches an arbitrary address.
"""

from __future__ import annotations

import os
import secrets
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import h5py

from hdf5_ptc.errors import refuse

#: Block size of the byte-range cache for a remote file; one HDF5 chunk often fits.
REMOTE_BLOCK_BYTES = 4 * 2**20
#: How many files one session may hold open.
MAX_OPEN_PER_SESSION = 32
RANGE_ORIGIN_ENV = "CLIO_SOURCE_RANGE_ORIGIN"


@dataclass
class OpenFile:
    """One open file: its handle, where it came from, and the h5py object."""

    handle: str
    owner: str
    source: str
    remote: bool
    h5: h5py.File
    size: int | None
    raw: Any = None
    reads: dict[str, int] = field(default_factory=lambda: {"requests": 0, "bytes": 0})

    def fetched(self) -> dict[str, int]:
        """Bytes and requests a remote file has pulled so far (zeros for a local file)."""
        cache = getattr(self.raw, "cache", None)
        info = getattr(getattr(cache, "_fetch_block_cached", None), "cache_info", None)
        if info is None:
            return dict(self.reads)
        misses = info().misses
        return {"requests": misses, "bytes": misses * REMOTE_BLOCK_BYTES}


def range_origin() -> str:
    """The URL prefix CLIO serves byte ranges under, or ``""`` when none is configured."""
    return os.environ.get(RANGE_ORIGIN_ENV, "").rstrip("/")


def _is_url(source: str) -> bool:
    return source.startswith(("http://", "https://"))


def _open_remote(url: str) -> tuple[h5py.File, Any, int | None]:
    origin = range_origin()
    if not origin:
        refuse(
            "range_origin_unconfigured",
            "this server opens byte-range URLs only from CLIO, and no range origin is set",
        )
    if not (url == origin or url.startswith(origin + "/")):
        refuse("url_not_allowed", f"only byte-range URLs under {origin} can be opened")
    import aiohttp  # noqa: PLC0415 - remote files only
    import fsspec  # noqa: PLC0415 - remote files only

    fs = fsspec.filesystem(
        "http",
        client_kwargs={
            "trust_env": True,
            "timeout": aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=120),
        },
        skip_instance_cache=True,
    )
    try:
        size = fs.size(url)
        raw = fs.open(url, "rb", block_size=REMOTE_BLOCK_BYTES, cache_type="blockcache")
        return h5py.File(raw, "r"), raw, size
    except FileNotFoundError:
        refuse("not_found", "the byte-range URL answered not found; it may have expired")
    except OSError as exc:
        refuse("open_failed", f"the file could not be read as HDF5: {exc}")
    raise AssertionError("unreachable")


def _open_local(path: str) -> tuple[h5py.File, int | None]:
    target = Path(path).expanduser()
    if not target.is_file():
        refuse("not_found", f"there is no file at {path}")
    try:
        return h5py.File(target, "r"), target.stat().st_size
    except OSError as exc:
        refuse("not_hdf5", f"{path} is not an HDF5 or NetCDF-4 file: {exc}")
    raise AssertionError("unreachable")


class Handles:
    """The open files of every session this server serves."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._files: dict[str, OpenFile] = {}

    def open(self, owner: str, source: str) -> OpenFile:
        with self._lock:
            held = [f for f in self._files.values() if f.owner == owner]
            for existing in held:
                if existing.source == source:
                    return existing
            if len(held) >= MAX_OPEN_PER_SESSION:
                refuse(
                    "too_many_open_files",
                    f"{MAX_OPEN_PER_SESSION} files are open; close one with close_file",
                )
        if _is_url(source):
            h5, raw, size = _open_remote(source)
        else:
            (h5, size), raw = _open_local(source), None
        opened = OpenFile(
            handle="f_" + secrets.token_hex(4),
            owner=owner,
            source=source,
            remote=raw is not None,
            h5=h5,
            size=size,
            raw=raw,
        )
        with self._lock:
            self._files[opened.handle] = opened
        return opened

    def get(self, owner: str, handle: str) -> OpenFile:
        with self._lock:
            found = self._files.get(handle)
        if found is None or found.owner != owner:
            refuse("unknown_handle", f"{handle} is not an open file; open it with open_file")
        assert found is not None
        return found

    def close(self, owner: str, handle: str) -> OpenFile:
        found = self.get(owner, handle)
        with self._lock:
            self._files.pop(handle, None)
        try:
            found.h5.close()
        finally:
            if found.raw is not None:
                found.raw.close()
        return found

    def owned(self, owner: str) -> list[OpenFile]:
        with self._lock:
            return [f for f in self._files.values() if f.owner == owner]
