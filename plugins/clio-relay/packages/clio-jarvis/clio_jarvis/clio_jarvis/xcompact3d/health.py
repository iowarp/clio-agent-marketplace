"""Tell a diverged or empty Xcompact3d run from a good one.

Incompact3d v5.0 stops a run whose velocity passes 100 with ``Velocity
diverged! SIMULATION IS STOPPED!`` and ``MPI_ABORT`` with error code 0, so the
launcher reports success. A velocity that turns NaN passes that check (``abs``
of NaN is never 100 or more) and the run goes on to its last step writing NaN
snapshots. :class:`SolverWatch` reads the solver's per-step lines, stops the
run as soon as it sees either, and :func:`verdict` writes ``clio-run-result.json``
in the run directory with the evidence a caller needs to adapt the case.
"""

from __future__ import annotations

import json
import math
import re
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

RESULT_FILE = "clio-run-result.json"
RESULT_SCHEMA = "clio.xcompact3d-run.v1"
#: Incompact3d's own limit on the velocity maximum; the watch applies it to the minimum too.
VELOCITY_LIMIT = 100.0

STEP = re.compile(r"Time step =\s*(\d+)\s*/\s*(\d+),\s*Time unit =\s*(\S+)")
STEP_SECONDS = re.compile(r"Time for this time step \(s\):\s*(\S+)")
SNAPSHOT = re.compile(r"^Writing snapshots =>\s*(\d+)\s*$")
STOPPED = re.compile(r"(Velocity|Scalar) diverged! SIMULATION IS STOPPED!")
CFL = re.compile(r"^(CFL [xyz]-direction|CFL limits|cfl_diff_sum)")


class SolverDiverged(RuntimeError):
    """Raised from the line callback, which makes jarvis-cd stop the run."""


class RunFailed(RuntimeError):
    """The run diverged, wrote nothing or failed; ``result`` is clio-run-result.json."""

    def __init__(self, message: str, result: dict[str, Any]) -> None:
        super().__init__(message)
        self.result = result


def _numbers(text: str) -> list[float]:
    values = []
    for token in text.split():
        try:
            values.append(float(token))
        except ValueError:
            continue
    return values


class SolverWatch:
    """A line callback that watches the solver and passes each line on to ``inner``."""

    def __init__(self, inner: Callable[[str, str], None] | None, *, velocity_limit: float) -> None:
        self.inner = inner
        self.velocity_limit = velocity_limit
        self.lock = threading.Lock()
        self.step: int | None = None
        self.ilast: int | None = None
        self.time: float | None = None
        self.step_seconds: list[float] = []
        self.snapshots_announced = 0
        self.velocity_min: list[float] | None = None
        self.velocity_max: list[float] | None = None
        self.divergence: list[float] | None = None
        self.stability: list[str] = []
        self.cause: str | None = None
        self.cause_line: str | None = None
        self.recent: deque[str] = deque(maxlen=12)

    def __getattr__(self, name: str) -> Any:
        # finalize and finalize_process belong to the progress and artifact callback.
        if name.startswith("finalize") and self.inner is not None:
            return getattr(self.inner, name)
        raise AttributeError(name)

    def __call__(self, stream_name: str, line: str) -> None:
        if self.inner is not None:
            self.inner(stream_name, line)
        found = self.observe(line)
        if found:
            raise SolverDiverged(found)

    def observe(self, line: str) -> str | None:
        """Record one output line; the cause when it shows the run diverged."""
        text = line.replace("\x00", "").strip()
        if not text:
            return None
        with self.lock:
            self.recent.append(text)
            if self.cause is not None:
                return None
            found = None
            if (match := STEP.search(text)) is not None:
                self.step, self.ilast = int(match.group(1)), int(match.group(2))
                try:
                    self.time = float(match.group(3))
                except ValueError:
                    self.time = None
            elif (match := STEP_SECONDS.search(text)) is not None:
                try:
                    self.step_seconds.append(float(match.group(1)))
                except ValueError:
                    pass
            elif (match := SNAPSHOT.match(text)) is not None:
                self.snapshots_announced = max(self.snapshots_announced, int(match.group(1)))
            elif STOPPED.search(text):
                found = "solver_stopped"
            elif text.startswith("U,V,W min="):
                self.velocity_min = _numbers(text.split("=", 1)[1])
                found = self._velocity(self.velocity_min)
            elif text.startswith("U,V,W max="):
                self.velocity_max = _numbers(text.split("=", 1)[1])
                found = self._velocity(self.velocity_max)
            elif text.startswith("DIV U"):
                self.divergence = _numbers(text.split("=", 1)[-1])
                if any(not math.isfinite(value) for value in self.divergence):
                    found = "nonfinite_divergence"
            elif CFL.match(text):
                self.stability = (self.stability + [text])[-8:]
            if found:
                self.cause, self.cause_line = found, text
            return found

    def _velocity(self, values: list[float]) -> str | None:
        if any(not math.isfinite(value) for value in values):
            return "nonfinite_velocity"
        if any(abs(value) >= self.velocity_limit for value in values):
            return "velocity_blowup"
        return None


_CAUSES = {
    "solver_stopped": "Xcompact3d stopped the run: the velocity passed its limit of 100",
    "nonfinite_velocity": "the velocity became NaN or infinite",
    "velocity_blowup": "the velocity grew past {limit:g}",
    "nonfinite_divergence": "the velocity divergence became NaN or infinite",
    "no_output": "the run ended without writing a snapshot",
    "launch_failed": "the solver exited before its first time step",
}


def has_snapshot(output: Path) -> bool:
    """True when the BP5 index holds a step: more than its 64-byte header."""
    try:
        return (output / "md.idx").stat().st_size > 64
    except OSError:
        return False


def verdict(
    watch: SolverWatch,
    *,
    run_dir: Path,
    output: Path,
    config: dict[str, Any],
    case: dict[str, Any],
    return_codes: dict[str, int] | None,
) -> dict[str, Any]:
    """Judge the run, write clio-run-result.json and return it."""
    ilast, ioutput = int(config["ilast"]), int(config["ioutput"])
    expected = ilast // ioutput if ioutput > 0 else 0
    # The solver announces each snapshot just before it writes it.
    written = max(watch.snapshots_announced, 1) if has_snapshot(output) else 0
    cause = watch.cause
    failed = any(code != 0 for code in (return_codes or {}).values())
    if cause is None and failed and watch.step is None:
        cause = "launch_failed"
    if cause is None and expected and written == 0:
        cause = "no_output"
    if cause == "no_output":
        status = "no_output"
    elif cause == "launch_failed":
        status = "failed"
    elif cause is not None:
        status = "diverged"
    else:
        status = "failed" if failed else "ok"
    seconds = watch.step_seconds
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "status": status,
        "cause": cause,
        "message": _CAUSES[cause].format(limit=watch.velocity_limit) if cause else None,
        "evidence_line": watch.cause_line,
        "step": watch.step,
        "ilast": ilast,
        "time": watch.time,
        "dt": float(config["dt"]),
        "reynolds": float(config["re"]),
        "snapshots_expected": expected,
        "snapshots_written": written,
        "velocity_min": watch.velocity_min,
        "velocity_max": watch.velocity_max,
        "divergence_max_mean": watch.divergence,
        "seconds_per_step": round(sum(seconds) / len(seconds), 4) if seconds else None,
        "stability_lines": watch.stability,
        "last_lines": list(watch.recent),
        "return_codes": return_codes,
        "case": {key: case[key] for key in ("case", "grid", "spacing", "decomposition", "cfl", "diffusion_number", "suggested_dt", "points_across_body") if key in case},
        "output": str(output),
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if status == "diverged":
        result["adapt"] = (
            "The case is numerically unstable. Lower dt (case.suggested_dt is the stability bound "
            "for the grid; halve it when the run diverged within it), and when it diverged in the "
            "first steps also check the body mask (points_across_body) and the decomposition."
        )
    elif status == "no_output":
        result["adapt"] = (
            "Nothing was written. Check that ioutput is at most ilast and that run_dir is writable; "
            "the last lines show where the solver stopped."
        )
    elif cause == "launch_failed":
        result["adapt"] = (
            "The solver never reached its first time step: the launch or its start failed. The last "
            "lines hold the launcher's message (rank placement, a missing library, MPI start-up); fix "
            "that, such as ranks per node against the allocation, before changing the case."
        )
    (run_dir / RESULT_FILE).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def describe(result: dict[str, Any], run_dir: Path) -> str:
    """One error message holding the evidence, for the launcher's log and the caller."""
    parts = [f"xcompact3d {result['status']}"]
    if result.get("message"):
        parts.append(f": {result['message']}")
    if result.get("step") is not None:
        parts.append(f" at step {result['step']}/{result['ilast']} (time {result['time']})")
    parts.append(f"; dt {result['dt']:g}")
    case = result.get("case") or {}
    if case.get("grid"):
        parts.append(f", grid {'x'.join(str(n) for n in case['grid'])}")
    if case.get("suggested_dt") is not None:
        parts.append(f", suggested_dt {case['suggested_dt']:g}")
    if result.get("velocity_max") is not None:
        parts.append(f", U,V,W max {result['velocity_max']}")
    parts.append(f"; snapshots {result['snapshots_written']}/{result['snapshots_expected']}")
    if result.get("evidence_line"):
        parts.append(f"; solver said: {result['evidence_line']}")
    parts.append(f"; details in {run_dir / RESULT_FILE}")
    return "".join(parts)
