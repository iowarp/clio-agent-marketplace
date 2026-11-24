"""WRF (ARW, real-data) as a clio-jarvis package.

``case_dir`` holds a case that real.exe already produced: ``wrfinput_d01``,
``wrfbdy_d01`` and the ``namelist.input`` they were made with, plus any
lookup tables the physics needs beyond WRF's own (such as the Thompson
``*.dat`` files of NCAR's benchmarks). The run directory links WRF's run
tables from the install (``$WRF_HOME/run``), then the case's files, and gets
a ``namelist.input`` with the run length, history interval and process grid
set. wrf.exe runs there under MPI; rank 0 writes its log to ``rsl.out.0000``,
which the package follows and turns into progress lines.

``case_url`` names a tar archive of the case instead: when ``case_dir`` lacks
it, the job fetches the archive on the site (:mod:`clio_jarvis._contract.fetch`)
and later runs reuse what landed.

The software is a Spack ``wrf`` (em_real, dmpar). A site that already built
one, as a Spack upstream or module, is reused as it is: the install plans
nothing to build.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from clio_jarvis._contract.base import ClioApplication
from clio_jarvis._contract.fetch import fetch_archive
from clio_jarvis._contract.spec import in_job

#: Files of $WRF_HOME/run that are not tables: the run writes its own namelist.
_NOT_TABLES = re.compile(r"(^namelist\.input|\.exe$|^README|^Makefile$|\.(?:csh|sh|py)$)")
_CASE_FILES = ("wrfinput_d01", "wrfbdy_d01", "namelist.input")
_TABLE_SUFFIXES = (".dat", ".TBL", ".tbl", ".formatted")
_TIMING = re.compile(r"^Timing for main: time (?P<time>\S+) on domain\s+1:\s+(?P<seconds>[0-9.]+) elapsed seconds")
_HISTORY = re.compile(r"^Timing for Writing (?P<file>wrfout_d01_\S+) for domain\s+1:")
_SUCCESS = "SUCCESS COMPLETE WRF"
RESULT_SCHEMA = "clio.wrf-run.v1"
RESULT_NAME = "clio-run-result.json"
#: WRF stops when a patch has fewer cells a side ("Minimum decomposed computational patch size").
MIN_PATCH = 10


def _near_square(ranks: int) -> tuple[int, int]:
    """WRF's own split of ``ranks`` (MPASPECT): the factor pair nearest square, x the smaller."""
    best = (1, ranks)
    for x in range(1, int(ranks**0.5) + 1):
        if ranks % x == 0:
            best = (x, ranks // x)
    return best


def max_ranks(e_we: int, e_sn: int) -> int:
    """The most processes WRF's own split allows on an ``e_we`` x ``e_sn`` grid."""
    for ranks in range(((e_we - 1) // MIN_PATCH) * ((e_sn - 1) // MIN_PATCH), 0, -1):
        px, py = _near_square(ranks)
        if min((e_we - 1) // px, (e_sn - 1) // py) >= MIN_PATCH:
            return ranks
    return 1


def namelist_value(text: str, name: str) -> str | None:
    """The first value of ``name`` in a Fortran namelist, as written."""
    match = re.search(rf"(?im)^\s*{re.escape(name)}\s*=\s*([^,\n!]+)", text)
    return match.group(1).strip().strip("'\"") if match else None


def set_namelist(text: str, group: str, name: str, value: Any) -> str:
    """Set ``name = value,`` in ``&group``, adding the line when the group lacks it."""
    if isinstance(value, bool):
        value = ".true." if value else ".false."
    line = f" {name:<24}= {value},"
    pattern = re.compile(rf"(?im)^[ \t]*{re.escape(name)}[ \t]*=.*$")
    start = re.search(rf"(?im)^\s*&{re.escape(group)}\b.*$", text)
    if start is None:
        return f"{text.rstrip()}\n&{group}\n{line}\n/\n"
    end = re.search(r"(?m)^\s*/\s*$", text[start.end():])
    stop = start.end() + (end.start() if end else len(text) - start.end())
    body = text[start.end():stop]
    if pattern.search(body):
        body = pattern.sub(line, body, count=1)
    else:
        body = f"{body.rstrip()}\n{line}\n"
    return text[: start.end()] + body + text[stop:]


def drop_namelist(text: str, name: str) -> str:
    """Remove every ``name = ...`` line."""
    return re.sub(rf"(?im)^[ \t]*{re.escape(name)}[ \t]*=.*\n?", "", text)


#: WRF reads these intervals in minutes, and its _d, _h, _m and _s forms win over the plain one.
_UNIT_FORMS = {"history_interval": ("_d", "_h", "_m", "_s"), "restart_interval": ("_d", "_h", "_m", "_s")}


def case_window(text: str) -> tuple[dt.datetime, dt.datetime]:
    """The start and end time of domain 1 in a namelist's &time_control."""

    def moment(prefix: str) -> dt.datetime:
        parts = [int(float(namelist_value(text, f"{prefix}_{unit}") or 0)) for unit in ("year", "month", "day", "hour", "minute", "second")]
        return dt.datetime(*parts)

    return moment("start"), moment("end")


class RslFollower:
    """Follows rank 0's ``rsl.out.0000`` and feeds its lines to the runtime callback.

    It adds one ``clio-wrf history N of M`` line after each history write past the
    first, which the contract's progress pattern counts, and holds the providers'
    end of the run until :meth:`release`, so clio-run-result.json is among the
    run's outputs.
    """

    def __init__(self, inner: Callable[[str, str], None] | None, log: Path, total: int) -> None:
        self.inner = inner
        self.log = log
        self.total = total
        self.lock = threading.Lock()
        self._emit_lock = threading.Lock()
        self.histories: list[str] = []
        self.step_seconds: list[float] = []
        self.model_time: str | None = None
        self.success = False
        self.exit_code: int | None = None
        self._done = threading.Event()
        self._thread = threading.Thread(target=self._follow, name="clio-wrf-rsl", daemon=True)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("finalize") and self.inner is not None:
            return getattr(self.inner, name)
        raise AttributeError(name)

    def __call__(self, stream_name: str, line: str) -> None:
        # The rsl tail thread and the launch's stdout reader both feed inner.
        if self.inner is not None:
            with self._emit_lock:
                self.inner(stream_name, line)

    def start(self) -> None:
        self._thread.start()

    def finalize_process(self, return_code: int) -> None:
        with self.lock:
            if self.exit_code in (None, 0):
                self.exit_code = return_code

    def stop(self) -> None:
        """Read the log to its end, then stop following."""
        self._done.set()
        self._thread.join(timeout=30)

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

    def observe(self, line: str) -> None:
        text = line.strip()
        timing = _TIMING.match(text)
        if timing:
            self.model_time = timing.group("time")
            self.step_seconds.append(float(timing.group("seconds")))
            return
        history = _HISTORY.match(text)
        if history:
            self.histories.append(history.group("file"))
            written = len(self.histories) - 1
            if written >= 1:
                mean = sum(self.step_seconds[-50:]) / max(1, len(self.step_seconds[-50:]))
                self(
                    "stdout",
                    f"clio-wrf history {written} of {self.total} {history.group('file')} "
                    f"model time {self.model_time} seconds per step {mean:.3f}",
                )
            return
        if _SUCCESS in text:
            self.success = True

    def _read_from(self, offset: int) -> bytes:
        # A fresh open each time: on a shared file system (NFS close-to-open) a handle kept
        # open does not see what rank 0 writes from another node until its attributes expire.
        try:
            with self.log.open("rb") as handle:
                handle.seek(offset)
                return handle.read()
        except FileNotFoundError:
            return b""

    def _follow(self) -> None:
        offset = 0
        pending = b""
        quiet = 0
        while True:
            finishing = self._done.is_set()
            chunk = self._read_from(offset)
            if chunk:
                offset += len(chunk)
                quiet = 0
                *lines, pending = (pending + chunk).split(b"\n")
                for raw in lines:
                    line = raw.decode("utf-8", errors="replace")
                    self("stdout", line)
                    self.observe(line)
                continue
            if finishing:
                # The launch has returned; read until the log stops growing for a few polls.
                quiet += 1
                if quiet >= 4:
                    if pending:
                        line = pending.decode("utf-8", errors="replace")
                        self("stdout", line)
                        self.observe(line)
                    return
            time.sleep(0.5)


class Wrf(ClioApplication):
    """WRF ARW on a real-data case with netCDF history output."""

    clio_program = "wrf.exe"
    clio_probe_arguments = None
    clio_capabilities = ("mpi_execution", "wrf_em_real", "netcdf_history")

    def _configure_menu(self) -> list[dict[str, Any]]:
        return [
            {"name": "nprocs", "msg": "MPI processes; WRF splits domain 1 into an nproc_x x nproc_y grid of patches (see the contract's sizing)", "type": int, "default": 40},
            {
                "name": "ppn",
                "msg": "MPI processes per node; empty means cores_per_node, else the physical cores of the job's node",
                "type": int,
                "default": None,
                "required": False,
            },
            {
                "name": "cores_per_node",
                "msg": "Physical cores per node of the target partition (relay's describe reports them); fills an empty ppn",
                "type": int,
                "default": None,
                "required": False,
            },
            {
                "name": "case_dir",
                "msg": "Absolute directory on the site with the real.exe output (wrfinput_d01, wrfbdy_d01) and its namelist.input, plus any physics tables (*.dat) the case needs",
                "type": str,
                "default": "",
            },
            {
                "name": "case_url",
                "msg": "https URL of a tar archive holding the case; when case_dir lacks the case, the job fetches it once and extracts only the case's files into case_dir",
                "type": str,
                "default": "",
            },
            {"name": "case_sha256", "msg": "The case archive's SHA-256; empty records the digest the fetch saw", "type": str, "default": ""},
            {"name": "run_minutes", "msg": "Simulated minutes from the case's start; must end within the boundary data, which the case's namelist end time marks", "type": int, "default": 180},
            {"name": "history_interval", "msg": "Simulated minutes between two history files (wrfout_d01_*)", "type": int, "default": 60},
            {"name": "time_step", "msg": "Model time step in seconds; empty keeps the case's (about 6 x dx in km)", "type": int, "default": None, "required": False},
            {"name": "nproc_x", "msg": "Patches along x; -1 lets WRF choose with nproc_y", "type": int, "default": -1},
            {"name": "nproc_y", "msg": "Patches along y; -1 lets WRF choose with nproc_x", "type": int, "default": -1},
            {"name": "run_dir", "msg": "Run directory; empty means {shared_dir}/run", "type": str, "default": ""},
            {"name": "walltime", "msg": "Wall-time limit in seconds; absent means no limit", "type": int, "default": None, "required": False},
            {"name": "queue", "msg": "Batch queue; empty means the site default", "type": str, "default": ""},
        ]

    def _clio_prepare(self, config: dict[str, Any]) -> None:
        case = Path(os.path.expanduser(str(config["case_dir"])))
        missing = [name for name in _CASE_FILES if not (case / name).is_file()]
        url = str(config.get("case_url") or "")
        if missing and url:
            if not in_job() and not self._clio_runs_here():
                # A scheduled pipeline configured on its submitting host: the job fetches.
                return
            fetch_archive(
                url,
                case,
                want=lambda name: name in _CASE_FILES or name.endswith(_TABLE_SUFFIXES),
                required=_CASE_FILES,
                sha256=str(config.get("case_sha256") or ""),
            )
            missing = []
        if missing:
            raise ValueError(
                f"case_dir {case} lacks {', '.join(missing)}: it must hold real.exe's output and its "
                "namelist.input, or set case_url to an archive of the case for the job to fetch"
            )
        text = (case / "namelist.input").read_text(encoding="utf-8", errors="replace")
        start, end = case_window(text)
        minutes = int(config["run_minutes"])
        stop = start + dt.timedelta(minutes=minutes)
        if stop > end:
            raise ValueError(
                f"run_minutes {minutes} ends at {stop:%Y-%m-%d_%H:%M:%S}, past the case's boundary data "
                f"({end:%Y-%m-%d_%H:%M:%S}); at most {int((end - start).total_seconds() // 60)}"
            )
        if minutes % int(config["history_interval"]):
            raise ValueError("run_minutes must be a whole number of history_interval")
        nx, ny, ranks = int(config["nproc_x"]), int(config["nproc_y"]), int(config["nprocs"])
        if nx > 0 and ny > 0 and nx * ny != ranks:
            raise ValueError(f"nproc_x x nproc_y is {nx * ny}, not nprocs {ranks}")
        grid = [int(float(namelist_value(text, name) or 0)) for name in ("e_we", "e_sn")]
        if all(grid):
            px, py = (nx, ny) if nx > 0 and ny > 0 else _near_square(ranks)
            if min((grid[0] - 1) // px, (grid[1] - 1) // py) < MIN_PATCH:
                raise ValueError(
                    f"{ranks} processes split the {grid[0]} x {grid[1]} grid into patches under "
                    f"{MIN_PATCH} cells a side; WRF stops. Use at most {max_ranks(grid[0], grid[1])} processes"
                )
        values: list[tuple[str, str, Any]] = [
            ("time_control", "run_days", 0),
            ("time_control", "run_hours", 0),
            ("time_control", "run_minutes", minutes),
            ("time_control", "run_seconds", 0),
            ("time_control", "history_interval", int(config["history_interval"])),
            ("time_control", "frames_per_outfile", 1),
            ("time_control", "restart", False),
            # No restart files inside the run: the benchmark's is about 1 GB each.
            ("time_control", "restart_interval", minutes * 10),
            ("domains", "nproc_x", int(config["nproc_x"])),
            ("domains", "nproc_y", int(config["nproc_y"])),
        ]
        for unit, value in zip(("year", "month", "day", "hour", "minute", "second"), (stop.year, stop.month, stop.day, stop.hour, stop.minute, stop.second)):
            values.append(("time_control", f"end_{unit}", value if unit == "year" else f"{value:02d}"))
        if config.get("time_step") not in (None, ""):
            values.append(("domains", "time_step", int(config["time_step"])))
        for group, name, value in values:
            for suffix in _UNIT_FORMS.get(name, ()):
                text = drop_namelist(text, name + suffix)
            text = set_namelist(text, group, name, value)
        run_dir = Path(config["run_dir"])
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "namelist.input").write_text(text, encoding="utf-8")
        facts = {
            "case_dir": str(case),
            "start": f"{start:%Y-%m-%d_%H:%M:%S}",
            "end": f"{stop:%Y-%m-%d_%H:%M:%S}",
            "boundary_end": f"{end:%Y-%m-%d_%H:%M:%S}",
            "grid": [namelist_value(text, name) for name in ("e_we", "e_sn", "e_vert")],
            "dx_m": namelist_value(text, "dx"),
            "time_step_s": namelist_value(text, "time_step"),
        }
        (run_dir / "clio-case.json").write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")

    def _wrf_home(self) -> Path:
        home = (self.mod_env or {}).get("WRF_HOME") or os.environ.get("WRF_HOME")
        if not home:
            found = shutil.which(self.clio_program, path=(self.mod_env or {}).get("PATH"))
            if found is None:
                raise RuntimeError("wrf.exe is not on the PATH of the install; is the wrf Spack install loaded?")
            home = str(Path(os.path.realpath(found)).parent.parent)
        return Path(home)

    def _link_inputs(self, run_dir: Path) -> None:
        """WRF's run tables, then the case's files over them."""
        tables = self._wrf_home() / "run"
        case = Path(os.path.expanduser(str(self.config["case_dir"])))
        links: dict[str, Path] = {}
        for source in sorted(tables.iterdir()) if tables.is_dir() else []:
            if not _NOT_TABLES.search(source.name):
                links[source.name] = source
        for source in sorted(case.iterdir()):
            if source.is_file() and source.name != "namelist.input" and (
                source.name in _CASE_FILES or source.suffix in _TABLE_SUFFIXES
            ):
                links[source.name] = source
        for name, source in links.items():
            target = run_dir / name
            if target.is_symlink() or target.exists():
                target.unlink()
            target.symlink_to(source.resolve())

    def _run_outputs(self, run_dir: Path) -> list[Path]:
        return [*run_dir.glob("wrfout_d01_*"), *run_dir.glob("wrfrst_d01_*"), *run_dir.glob("rsl.*"), run_dir / RESULT_NAME]

    def start(self) -> None:
        self._clio_ensure_configured(prepare=True)
        run_dir = Path(self.config["run_dir"])
        for path in self._run_outputs(run_dir):
            if path.exists():
                path.unlink()
        self._link_inputs(run_dir)
        total = int(self.config["run_minutes"]) // int(self.config["history_interval"])
        follower = RslFollower(self.runtime_line_callback(), run_dir / "rsl.out.0000", total)
        follower.start()
        began = time.monotonic()
        try:
            codes = self._clio_mpi(self.clio_executable(), cwd=str(run_dir), line_callback=follower, check=False)
        finally:
            follower.stop()
        try:
            result = self._verdict(run_dir, follower, codes, time.monotonic() - began)
        finally:
            follower.release()
        print(f"clio-wrf result {json.dumps({k: result[k] for k in ('status', 'cause', 'history_written', 'history_expected')})}", flush=True)
        if result["status"] != "ok":
            raise RuntimeError(f"wrf failed: {result['cause']}; see {run_dir}/rsl.error.0000")

    def _verdict(self, run_dir: Path, follower: RslFollower, codes: dict[str, int], seconds: float) -> dict[str, Any]:
        total = int(self.config["run_minutes"]) // int(self.config["history_interval"])
        written = max(0, len(follower.histories) - 1)
        failures = {host: code for host, code in codes.items() if code != 0}
        cause = None
        if failures:
            cause = f"wrf.exe exited {failures}"
        elif not follower.success:
            cause = f"rsl.out.0000 has no '{_SUCCESS}'"
        elif written < total:
            cause = f"{written} of {total} history intervals written"
        tail: list[str] = []
        error_log = run_dir / "rsl.error.0000"
        if cause and error_log.is_file():
            tail = error_log.read_text(encoding="utf-8", errors="replace").splitlines()[-20:]
        steps = follower.step_seconds
        result = {
            "schema": RESULT_SCHEMA,
            "status": "ok" if cause is None else "failed",
            "cause": cause,
            "model_time": follower.model_time,
            "history_written": written,
            "history_expected": total,
            "history_files": follower.histories,
            "steps": len(steps),
            "seconds_per_step": round(sum(steps[1:]) / max(1, len(steps) - 1), 4) if steps else None,
            "first_step_seconds": steps[0] if steps else None,
            "wall_seconds": round(seconds, 1),
            "nprocs": int(self.config["nprocs"]),
            "return_codes": codes,
            "error_tail": tail,
        }
        (run_dir / RESULT_NAME).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return result

    def stop(self) -> None:
        """WRF runs to its end time."""

    def clean(self) -> None:
        self._clio_ensure_configured(prepare=False)
        for path in self._run_outputs(Path(self.config["run_dir"])):
            if path.exists():
                path.unlink()
