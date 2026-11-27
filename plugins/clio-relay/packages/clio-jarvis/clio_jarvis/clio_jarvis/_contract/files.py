"""File sizes that a shared file system cannot serve stale.

A network file system client caches a file's attributes. A ``stat()`` on a
node that did not write the file can return the size it saw seconds or
minutes ago, so a finished run looks empty. Opening the file makes the
client revalidate them (close-to-open consistency), so :func:`fresh_size`
opens the file and asks the open descriptor.

The client also remembers that a name did not exist. A node that looked for a
file before another node created it can keep failing ``open()`` for minutes,
while listing the parent directory shows the new name at once. So when the
open finds nothing, :func:`fresh_size` lists the directories above the file
and tries once more.
"""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from pathlib import Path


def _relist_parents(path: Path | str) -> None:
    """List the directories above ``path``, nearest existing one first and then downward."""
    chain = list(Path(os.path.abspath(path)).parents)
    for found, directory in enumerate(chain):
        try:
            os.listdir(directory)
        except OSError:
            continue
        for below in reversed(chain[:found]):
            try:
                os.listdir(below)
            except OSError:
                return
        return


def fresh_size(path: Path | str) -> int:
    """The size of ``path`` as the file server holds it now; raises ``OSError``."""
    try:
        fd = os.open(path, os.O_RDONLY)
    except FileNotFoundError:
        _relist_parents(path)
        fd = os.open(path, os.O_RDONLY)
    try:
        return os.fstat(fd).st_size
    finally:
        os.close(fd)


@contextmanager
def revealing(path: Path | str, interval: float = 1.0):
    """While the block runs, list the directories above ``path`` until this node sees it.

    A package removes the last run's output before it launches the solver, so
    the node running JARVIS has just looked the name up and found nothing. A
    viewer on that node (say pvserver's rank 0) would keep being told the new
    output does not exist; one listing of its directory after the solver
    creates it clears that for every process on the node.
    """
    done = threading.Event()

    def watch() -> None:
        while not done.is_set():
            if os.path.exists(path):
                return
            _relist_parents(path)
            done.wait(interval)

    thread = threading.Thread(target=watch, name="clio-reveal", daemon=True)
    thread.start()
    try:
        yield
    finally:
        done.set()
        thread.join(timeout=interval + 5)
