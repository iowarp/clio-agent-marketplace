"""WarpX (3D, electromagnetic particle-in-cell) as a clio-jarvis package.

``inputs`` names a WarpX inputs file, the solver's own format (AMReX
ParmParse ``key = value`` lines), and the package runs it as written. The
run directory gets a copy of it as ``inputs``; the command line then sets
``max_step`` and adds one diagnostic of the package's own, ``clio``, that
writes AMReX plotfiles every ``plot_interval`` steps beside the inputs' own
diagnostics.

WarpX writes a plotfile in place, its Header first and the field data after,
so a viewer that opened it at once would read half a file. The ``clio``
diagnostic writes into ``writing/``; WarpX flushes a step's diagnostics
before it prints ``STEP N ends.``, so on that line the package moves every
plotfile up to iteration N into ``plotfiles/`` and prints one
``clio-warpx plotfile I of M`` line, which the contract's progress pattern
counts. ``plotfiles/plt*`` is then a series of whole plotfiles that
ParaView's AMReX reader follows as it grows.

The software is a Spack ``warpx`` (3D, MPI, no OpenMP). MPI, the launcher,
the nodes and the ranks per node come from JARVIS and the site's resource
graph through the launch, never from this package.
"""

from __future__ import annotations

import json
import math
import os
import re
import shlex
import shutil
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from clio_jarvis._contract.base import ClioApplication
from clio_jarvis._contract.files import _relist_parents

RESULT_SCHEMA = "clio.warpx-run.v1"
RESULT_NAME = "clio-run-result.json"
CASE_NAME = "clio-case.json"
INPUTS_NAME = "inputs"
DIAG = "clio"
WRITING = "writing"
PLOTFILES = "plotfiles"
PREFIX = "plt"
DIGITS = 6
#: AMReX's own max_grid_size in 3D when the inputs set none.
AMREX_MAX_GRID_3D = 32
_STEP_ENDS = re.compile(r"^STEP (?P<step>\d+) ends\.\s+TIME = (?P<time>\S+)")
_PLOTFILE = re.compile(rf"^{PREFIX}(?P<iteration>\d{{{DIGITS},}})$")
#: Keys the package sets on the command line; the inputs' values of these give way.
_OWN_KEYS = ("max_step", "stop_time", "warpx.verbose")


def parse_inputs(text: str) -> dict[str, str]:
    """The ``key = value`` definitions of a ParmParse file; the last one of a key wins."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and " " not in key:
            values[key] = value.strip()
    return values


def _ints(value: str | None) -> list[int]:
    try:
        return [int(float(token)) for token in (value or "").replace('"', " ").split()]
    except ValueError:
        return []


def box_count(values: dict[str, str]) -> int | None:
    """Level-0 boxes of the grid: ceil(n_cell / max_grid_size) along each axis multiplied."""
    cells = _ints(values.get("amr.n_cell"))
    if len(cells) != 3:
        return None
    sizes = _ints(values.get("amr.max_grid_size")) or [AMREX_MAX_GRID_3D]
    sizes = (sizes * 3)[:3]
    for axis, name in enumerate("xyz"):
        own = _ints(values.get(f"amr.max_grid_size_{name}"))
        if own:
            sizes[axis] = own[0]
    if min(sizes) < 1:
        return None
    return math.prod(-(-cell // size) for cell, size in zip(cells, sizes))


def plotfile_name(iteration: int) -> str:
    return f"{PREFIX}{iteration:0{DIGITS}d}"


def plotfile_time(path: Path) -> float | None:
    """The simulated time an AMReX plotfile's Header records."""
    try:
        lines = (path / "Header").read_text(encoding="ascii", errors="replace").splitlines()
        count = int(lines[1])
        return float(lines[2 + count + 1])
    except (OSError, ValueError, IndexError):
        return None


class PlotfilePublisher:
    """Watches WarpX's stdout and moves each written plotfile where the viewer follows.

    It passes every line on to the runtime callback, and holds the providers'
    end of the run until :meth:`release`, so clio-run-result.json is among the
    run's outputs.
    """

    def __init__(self, inner: Callable[[str, str], None] | None, run_dir: Path, interval: int, total: int) -> None:
        self.inner = inner
        self.writing = run_dir / WRITING
        self.plotfiles = run_dir / PLOTFILES
        self.interval = interval
        self.total = total
        self.lock = threading.Lock()
        self.published: list[str] = []
        self.step = 0
        self.time: str | None = None
        self.step_wall: list[float] = []
        self.exit_code: int | None = None
        self._last_end: float | None = None

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
        ends = _STEP_ENDS.match(line.strip())
        if ends:
            now = time.monotonic()
            with self.lock:
                if self._last_end is not None:
                    self.step_wall.append(now - self._last_end)
                self._last_end = now
                self.step, self.time = int(ends.group("step")), ends.group("time")
            self.publish(up_to=int(ends.group("step")))

    def finalize_process(self, return_code: int) -> None:
        with self.lock:
            if self.exit_code in (None, 0):
                self.exit_code = return_code

    def _listing(self) -> list[str]:
        try:
            return os.listdir(self.writing)
        except FileNotFoundError:
            _relist_parents(self.writing / PREFIX)
        try:
            return os.listdir(self.writing)
        except FileNotFoundError:
            return []

    def publish(self, up_to: int | None) -> None:
        """Move the written plotfiles up to iteration ``up_to`` (all with None), oldest first."""
        with self.lock:
            ready = sorted(
                (int(found.group("iteration")), name)
                for name in self._listing()
                if (found := _PLOTFILE.match(name)) and (up_to is None or int(found.group("iteration")) <= up_to)
            )
            for iteration, name in ready:
                source = self.writing / name
                if not (source / "Header").is_file():
                    continue
                self.plotfiles.mkdir(parents=True, exist_ok=True)
                target = self.plotfiles / name
                if target.exists():
                    shutil.rmtree(target)
                os.rename(source, target)
                self.published.append(name)
                if iteration == 0:
                    self.emit(f"clio-warpx initial plotfile {name}")
                    continue
                recent = self.step_wall[-50:]
                seconds = sum(recent) / max(1, len(recent))
                self.emit(
                    f"clio-warpx plotfile {iteration // self.interval} of {self.total} {name} "
                    f"iteration {iteration} time {plotfile_time(target)} seconds per step {seconds:.3f}"
                )

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


class Warpx(ClioApplication):
    """WarpX 3D on a native inputs file, with a growing series of AMReX plotfiles."""

    clio_program = "warpx.3d"
    clio_probe_arguments = None
    clio_capabilities = ("mpi_execution", "warpx_3d", "amrex_plotfile")

    def _configure_menu(self) -> list[dict[str, Any]]:
        return [
            {"name": "nprocs", "msg": "MPI processes; WarpX spreads the grid's boxes over them (see the contract's sizing)", "type": int, "default": 8},
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
                "name": "inputs",
                "msg": (
                    "WarpX inputs file (3D, the solver's own key = value format) holding the whole case: "
                    "geometry.dims = 3, amr.n_cell, the domain, boundaries, species, lasers and any "
                    "diagnostics of its own. A relative path is from the directory jarvis runs in, and "
                    "{pkg_dir} names this package"
                ),
                "type": str,
                "default": "",
            },
            {"name": "max_step", "msg": "Time steps to run; it replaces the inputs' max_step and stop_time", "type": int, "default": 400},
            {"name": "plot_interval", "msg": "Time steps between two plotfiles of the live view; max_step must be a whole number of them", "type": int, "default": 20},
            {
                "name": "fields",
                "msg": "Fields in each plotfile, space separated, from Ex Ey Ez Bx By Bz jx jy jz rho (and a species' rho_<name>)",
                "type": str,
                "default": "Ex Ey Ez Bx By Bz jx jy jz rho",
            },
            {"name": "plot_particles", "msg": "Write the species' particles into each plotfile too (larger plotfiles)", "type": bool, "default": False},
            {"name": "run_dir", "msg": "Run directory; empty means {shared_dir}/run", "type": str, "default": ""},
            {"name": "walltime", "msg": "Wall-time limit in seconds; absent means no limit", "type": int, "default": None, "required": False},
            {"name": "queue", "msg": "Batch queue; empty means the site default", "type": str, "default": ""},
        ]

    def _clio_prepare(self, config: dict[str, Any]) -> None:
        steps, interval = int(config["max_step"]), int(config["plot_interval"])
        if steps % interval:
            raise ValueError(f"max_step {steps} must be a whole number of plot_interval {interval}")
        source = Path(str(config["inputs"]).replace("{pkg_dir}", str(self.pkg_dir))).expanduser()
        source = source if source.is_absolute() else Path(os.getcwd()) / source
        if not source.is_file():
            raise FileNotFoundError(f"inputs {source} does not exist; stage the WarpX inputs file with the job")
        run_dir = Path(config["run_dir"])
        run_dir.mkdir(parents=True, exist_ok=True)
        target = run_dir / INPUTS_NAME
        if source.resolve() != target.resolve():
            shutil.copyfile(source, target)
        config["inputs"] = self.config["inputs"] = str(target)
        values = parse_inputs(target.read_text(encoding="utf-8", errors="replace"))
        dims = values.get("geometry.dims", "3").strip('"')
        if dims != "3":
            raise ValueError(f"inputs set geometry.dims = {dims}; this package runs the 3D WarpX, so set geometry.dims = 3")
        if len(_ints(values.get("amr.n_cell"))) != 3:
            raise ValueError("inputs need amr.n_cell with three cell counts (nx ny nz)")
        if DIAG in self._their_diagnostics(values):
            raise ValueError(f"inputs already name a diagnostic {DIAG!r}; the package adds its own under that name, so rename yours")
        facts = {
            "inputs": str(target),
            "n_cell": _ints(values.get("amr.n_cell")),
            "max_grid_size": values.get("amr.max_grid_size", f"{AMREX_MAX_GRID_3D} (AMReX's default)"),
            "boxes": box_count(values),
            "nprocs": int(config["nprocs"]),
            "prob_lo": values.get("geometry.prob_lo"),
            "prob_hi": values.get("geometry.prob_hi"),
            "species": (values.get("particles.species_names") or "").split(),
            "lasers": (values.get("lasers.names") or "").split(),
            "their_diagnostics": self._their_diagnostics(values),
            "replaced": {key: values[key] for key in _OWN_KEYS if key in values},
            "max_step": steps,
            "plot_interval": interval,
            "plotfiles_expected": steps // interval + 1,
        }
        (run_dir / CASE_NAME).write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _their_diagnostics(values: dict[str, str]) -> list[str]:
        names = (values.get("diagnostics.diags_names") or "").replace('"', " ").split()
        return [name for name in names if name.lower() != "none"]

    def clio_executable(self) -> str:
        """``warpx.3d``, else the one WarpX build named ``warpx.3d.<options>`` on the install's PATH."""
        path = (self.mod_env or {}).get("PATH") or os.environ.get("PATH", "")
        if shutil.which(self.clio_program, path=path):
            return self.clio_program
        for folder in path.split(os.pathsep):
            if not folder or not os.path.isdir(folder):
                continue
            runnable = [item for item in sorted(Path(folder).glob(f"{self.clio_program}.*")) if os.access(item, os.X_OK)]
            if runnable:
                return str(runnable[0])
        return self.clio_program

    def _command(self, run_dir: Path) -> str:
        values = parse_inputs((run_dir / INPUTS_NAME).read_text(encoding="utf-8", errors="replace"))
        names = [*self._their_diagnostics(values), DIAG]
        overrides = [
            f"max_step={int(self.config['max_step'])}",
            # max_step decides the run's length; a stop_time in the inputs would end it sooner.
            "stop_time=1.0e+300",
            "warpx.verbose=1",
            f"diagnostics.diags_names={' '.join(names)}",
            f"{DIAG}.diag_type=Full",
            f"{DIAG}.format=plotfile",
            f"{DIAG}.intervals={int(self.config['plot_interval'])}",
            f"{DIAG}.file_prefix={run_dir / WRITING / PREFIX}",
            f"{DIAG}.file_min_digits={DIGITS}",
            f"{DIAG}.fields_to_plot={' '.join(str(self.config['fields']).split())}",
            f"{DIAG}.write_species={1 if self.config.get('plot_particles') else 0}",
            # max_step is a whole number of plot_interval, so the last step has its plotfile already.
            f"{DIAG}.dump_last_timestep=0",
        ]
        return " ".join([shlex.quote(self.clio_executable()), INPUTS_NAME, *(shlex.quote(item) for item in overrides)])

    def _run_outputs(self, run_dir: Path) -> list[Path]:
        return [run_dir / WRITING, run_dir / PLOTFILES, run_dir / RESULT_NAME, run_dir / "warpx_used_inputs"]

    def _remove_outputs(self, run_dir: Path) -> None:
        for path in self._run_outputs(run_dir):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()

    def start(self) -> None:
        self._clio_ensure_configured(prepare=True)
        run_dir = Path(self.config["run_dir"])
        # A rerun starts a fresh series; a viewer must not see the last run's plotfiles.
        self._remove_outputs(run_dir)
        (run_dir / WRITING).mkdir(parents=True)
        (run_dir / PLOTFILES).mkdir(parents=True)
        interval = int(self.config["plot_interval"])
        publisher = PlotfilePublisher(self.runtime_line_callback(), run_dir, interval, int(self.config["max_step"]) // interval)
        began = time.monotonic()
        try:
            codes = self._clio_mpi(self._command(run_dir), cwd=str(run_dir), line_callback=publisher, check=False)
        finally:
            publisher.publish(up_to=None)
        try:
            result = self._verdict(run_dir, publisher, codes, time.monotonic() - began)
        finally:
            publisher.release()
        summary = {key: result[key] for key in ("status", "cause", "plotfiles_written", "plotfiles_expected")}
        print(f"clio-warpx result {json.dumps(summary)}", flush=True)
        if result["status"] != "ok":
            raise RuntimeError(f"warpx failed: {result['cause']}; see the job's output")

    def _verdict(self, run_dir: Path, publisher: PlotfilePublisher, codes: dict[str, int], seconds: float) -> dict[str, Any]:
        steps = int(self.config["max_step"])
        expected = steps // int(self.config["plot_interval"]) + 1
        written = len(publisher.published)
        failures = {host: code for host, code in codes.items() if code != 0}
        cause = None
        if failures:
            cause = f"warpx exited {failures}"
        elif publisher.step < steps:
            cause = f"the run reached step {publisher.step} of {steps}"
        elif written < expected:
            cause = f"{written} of {expected} plotfiles written"
        walls = publisher.step_wall
        result = {
            "schema": RESULT_SCHEMA,
            "status": "ok" if cause is None else "failed",
            "cause": cause,
            "step": publisher.step,
            "max_step": steps,
            "time": publisher.time,
            "plotfiles_written": written,
            "plotfiles_expected": expected,
            "plotfiles": publisher.published,
            "seconds_per_step": round(sum(walls) / len(walls), 4) if walls else None,
            "wall_seconds": round(seconds, 1),
            "nprocs": int(self.config["nprocs"]),
            "return_codes": codes,
        }
        (run_dir / RESULT_NAME).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return result

    def stop(self) -> None:
        """WarpX runs to max_step."""

    def clean(self) -> None:
        self._clio_ensure_configured(prepare=False)
        self._remove_outputs(Path(self.config["run_dir"]))
