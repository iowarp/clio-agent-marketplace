"""A publisher that polls a solver's output while it runs and passes its stdout on.

The MPI launch hands every stdout line to the publisher, which passes it on to
the runtime callback (the progress and artifact providers) and may read it. A
thread calls :meth:`poll` every second to publish what the solver has written
whole. The publisher holds the providers' end of the run until
:meth:`release`, so a result file the package writes afterwards is among the
run's outputs.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


class PollingPublisher:
    poll_seconds = 1.0

    def __init__(self, inner: Callable[[str, str], None] | None) -> None:
        self.inner = inner
        self.lock = threading.Lock()
        self.exit_code: int | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._watch, daemon=True)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("finalize") and self.inner is not None:
            return getattr(self.inner, name)
        raise AttributeError(name)

    def emit(self, line: str) -> None:
        # The providers read whole lines, as the MPI launch hands them over: with their newline.
        if self.inner is not None:
            self.inner("stdout", line if line.endswith("\n") else line + "\n")

    def __call__(self, stream_name: str, line: str) -> None:
        if self.inner is not None:
            self.inner(stream_name, line)
        self.read_line(line.strip())

    def read_line(self, line: str) -> None:
        """Look at one stdout line of the solver."""

    def poll(self, final: bool) -> None:
        """Publish what the solver has written whole; ``final`` once it has exited."""

    def _watch(self) -> None:
        while not self._stop.wait(self.poll_seconds):
            self.poll(final=False)

    def start(self) -> None:
        self._thread.start()

    def finish(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join()
        self.poll(final=True)

    def finalize_process(self, return_code: int) -> None:
        with self.lock:
            if self.exit_code in (None, 0):
                self.exit_code = return_code

    def release(self) -> None:
        with self.lock:
            code, self.exit_code = self.exit_code, None
        if code is None or self.inner is None:
            return
        finalizer = getattr(self.inner, "finalize_process", None)
        if callable(finalizer):
            finalizer(code)
        elif callable(plain := getattr(self.inner, "finalize", None)):
            plain()
