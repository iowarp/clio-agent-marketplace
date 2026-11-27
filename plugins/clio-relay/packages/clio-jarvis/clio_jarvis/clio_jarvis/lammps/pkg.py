"""LAMMPS (classical molecular dynamics) as a clio-jarvis package.

``script`` names a native LAMMPS input script, the person's whole case
(units, atom style, the box and atoms or read_data, pair style, fixes and its
run commands), and the package runs it as written. The run directory gets a
copy of it as ``in.lammps`` beside copies of the ``data_files`` it reads.

The one thing the package adds is a dump of its own, ``clio``, inserted just
before the script's first ``run``: every ``dump_interval`` steps it writes one
text frame (atom id, type, position and velocity) to ``dumps/``. A publisher
thread reads each frame once it holds all its atoms, writes it as a VTK
PolyData file ``frames/frame_<step>.vtp`` (atoms as points, the simulated time
as TimeValue) and prints ``clio-lammps frame I of M``, which the contract's
progress pattern counts. ``frames/frame_*.vtp`` is a series of whole frames
that ParaView's XML PolyData reader follows as it grows.

The software is a Spack ``lammps`` with MPI. MPI, the launcher, the nodes and
the ranks per node come from JARVIS and the site's resource graph through the
launch, never from this package.
"""

from __future__ import annotations

import json
import math
import os
import re
import shlex
import shutil
import time
from array import array
from collections.abc import Callable
from pathlib import Path
from typing import Any

from clio_jarvis._contract.base import ClioApplication
from clio_jarvis._contract.points import write_points_vtp
from clio_jarvis._contract.publisher import PollingPublisher

RESULT_SCHEMA = "clio.lammps-run.v1"
RESULT_NAME = "clio-run-result.json"
CASE_NAME = "clio-case.json"
SCRIPT_NAME = "in.lammps"
RUN_SCRIPT_NAME = "clio-run.lammps"
LOG_NAME = "log.lammps"
DUMP = "clio"
DUMPS = "dumps"
FRAMES = "frames"
DIGITS = 10
_DUMP_FILE = re.compile(r"^dump\.(?P<step>\d+)\.txt$")
_COMMAND = re.compile(r"^\s*(?P<word>[A-Za-z_][\w/]*)(?P<rest>.*)$")
#: Commands that make the run lines of the text an unreliable count of the steps.
_FLOW_COMMANDS = {"jump", "label", "next", "include", "clear"}
_PERFORMANCE = re.compile(r"^Performance:\s*(?P<text>.+)$")
_LOOP_TIME = re.compile(r"^Loop time of (?P<seconds>[\d.eE+-]+) on (?P<procs>\d+) procs for (?P<steps>\d+) steps")


def script_commands(text: str) -> list[tuple[int, str, list[str]]]:
    """The script's commands as (first line index, command, arguments), comments and & joins resolved."""
    commands: list[tuple[int, str, list[str]]] = []
    pending, start = "", 0
    for index, raw in enumerate(text.splitlines()):
        line = raw.split("#", 1)[0].rstrip()
        if not pending:
            start = index
        if line.endswith("&"):
            pending += line[:-1] + " "
            continue
        line, pending = pending + line, ""
        found = _COMMAND.match(line)
        if found:
            commands.append((start, found.group("word"), found.group("rest").split()))
    return commands


def run_steps(commands: list[tuple[int, str, list[str]]]) -> int | None:
    """The steps the script's run commands add up to, or None when the text cannot tell."""
    if any(word in _FLOW_COMMANDS for _, word, _ in commands):
        return None
    total = 0
    for _, word, args in commands:
        if word != "run":
            continue
        if not args or not args[0].isdigit() or "upto" in args[1:]:
            return None
        total += int(args[0])
    return total


def read_dump_frame(path: Path) -> dict[str, Any] | None:
    """One text dump frame, or None while LAMMPS has not written all its atoms yet."""
    try:
        text = path.read_text(encoding="ascii", errors="replace")
    except OSError:
        return None
    if not text.endswith("\n"):
        return None
    lines = text.splitlines()
    frame: dict[str, Any] = {"time": None, "box": []}
    index = 0
    try:
        while index < len(lines):
            item = lines[index].strip()
            index += 1
            if item.startswith("ITEM: TIMESTEP"):
                frame["step"] = int(lines[index])
                index += 1
            elif item.startswith("ITEM: TIME"):
                frame["time"] = float(lines[index])
                index += 1
            elif item.startswith("ITEM: NUMBER OF ATOMS"):
                frame["count"] = int(lines[index])
                index += 1
            elif item.startswith("ITEM: BOX BOUNDS"):
                frame["box"] = [float(value) for row in lines[index : index + 3] for value in row.split()[:2]]
                index += 3
            elif item.startswith("ITEM: ATOMS"):
                columns = item.split()[2:]
                rows = [row.split() for row in lines[index:]]
                if "count" not in frame or len(rows) != frame["count"] or any(len(row) != len(columns) for row in rows):
                    return None
                frame["columns"], frame["rows"] = columns, rows
                return frame
    except (ValueError, IndexError):
        return None
    return None


def frame_to_vtp(frame: dict[str, Any], target: Path) -> None:
    columns: list[str] = frame["columns"]
    rows: list[list[str]] = frame["rows"]
    at = {name: columns.index(name) for name in columns}
    positions = [float(row[at[axis]]) for row in rows for axis in ("x", "y", "z")]
    arrays: dict[str, tuple[array, int]] = {
        "id": (array("i", (int(row[at["id"]]) for row in rows)), 1),
        "type": (array("i", (int(row[at["type"]]) for row in rows)), 1),
    }
    if {"vx", "vy", "vz"} <= at.keys():
        velocity = [float(row[at[axis]]) for row in rows for axis in ("vx", "vy", "vz")]
        arrays["velocity"] = (array("f", velocity), 3)
        speeds = (math.sqrt(sum(v * v for v in velocity[i : i + 3])) for i in range(0, len(velocity), 3))
        arrays["speed"] = (array("f", speeds), 1)
    write_points_vtp(
        target,
        positions,
        arrays,
        time=frame["time"] if frame["time"] is not None else frame["step"],
        field_arrays={"timestep": [frame["step"]], "box_bounds": frame["box"]},
    )


def frame_name(step: int) -> str:
    return f"frame_{step:0{DIGITS}d}.vtp"


class FramePublisher(PollingPublisher):
    """Turns each whole dump frame into a .vtp in frames/, oldest first, while LAMMPS runs."""

    def __init__(self, inner: Callable[[str, str], None] | None, run_dir: Path, total: int) -> None:
        super().__init__(inner)
        self.dumps = run_dir / DUMPS
        self.frames = run_dir / FRAMES
        self.total = total
        self.published: list[int] = []
        self.skipped: list[int] = []
        self.atoms: int | None = None
        self.loop: dict[str, Any] = {}
        self.performance: list[str] = []
        self._began = time.monotonic()

    def read_line(self, line: str) -> None:
        if found := _LOOP_TIME.match(line):
            with self.lock:
                self.loop = {
                    "seconds": float(found.group("seconds")),
                    "procs": int(found.group("procs")),
                    "steps": int(found.group("steps")),
                }
        elif found := _PERFORMANCE.match(line):
            with self.lock:
                self.performance.append(found.group("text"))

    def poll(self, final: bool) -> None:
        """Publish every frame that holds all its atoms, oldest first."""
        with self.lock:
            try:
                names = os.listdir(self.dumps)
            except FileNotFoundError:
                return
            ready = sorted((int(found.group("step")), name) for name in names if (found := _DUMP_FILE.match(name)))
            done = {*self.published, *self.skipped}
            for position, (step, name) in enumerate(ready):
                if step in done:
                    continue
                frame = read_dump_frame(self.dumps / name)
                if frame is None:
                    # A later frame, or the end of the run, means LAMMPS has written all it will of this one.
                    if final or position < len(ready) - 1:
                        self.skipped.append(step)
                        self.emit(f"clio-lammps frame at timestep {step} is incomplete; skipped")
                    continue
                frame_to_vtp(frame, self.frames / frame_name(step))
                self.published.append(step)
                self.atoms = frame["count"]
                self.emit(
                    f"clio-lammps frame {len(self.published) - 1} of {self.total} {frame_name(step)} "
                    f"timestep {step} time {frame['time']} atoms {frame['count']} "
                    f"wall {time.monotonic() - self._began:.1f}"
                )


class Lammps(ClioApplication):
    """LAMMPS on a native input script, with a growing series of particle frames."""

    clio_program = "lmp"
    clio_probe_arguments = None
    clio_capabilities = ("mpi_execution", "lammps", "particle_frames")

    def _configure_menu(self) -> list[dict[str, Any]]:
        return [
            {"name": "nprocs", "msg": "MPI processes; LAMMPS gives each rank one brick of the box (see the contract's sizing)", "type": int, "default": 8},
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
                "name": "script",
                "msg": (
                    "LAMMPS input script (the solver's own command language) holding the whole case: units, "
                    "atom_style, the box and atoms (lattice, region, create_box, create_atoms, or read_data), "
                    "masses, pair_style and coefficients, velocities, fixes and its run commands. A relative "
                    "path is from the directory jarvis runs in, and {pkg_dir} names this package"
                ),
                "type": str,
                "default": "",
            },
            {
                "name": "data_files",
                "msg": "Other files the script reads (read_data files, potential files), space separated; each is copied into run_dir under its own name",
                "type": str,
                "default": "",
            },
            {"name": "steps", "msg": "Time steps the script's run commands add up to; checked against them when they are plain numbers", "type": int, "default": 10000},
            {"name": "dump_interval", "msg": "Time steps between two frames of the live view; steps must be a whole number of them", "type": int, "default": 100},
            {"name": "run_dir", "msg": "Run directory; empty means {shared_dir}/run", "type": str, "default": ""},
            {"name": "walltime", "msg": "Wall-time limit in seconds; absent means no limit", "type": int, "default": None, "required": False},
            {"name": "queue", "msg": "Batch queue; empty means the site default", "type": str, "default": ""},
        ]

    def _source(self, value: str) -> Path:
        path = Path(value.replace("{pkg_dir}", str(self.pkg_dir))).expanduser()
        return path if path.is_absolute() else Path(os.getcwd()) / path

    def _clio_prepare(self, config: dict[str, Any]) -> None:
        steps, interval = int(config["steps"]), int(config["dump_interval"])
        if steps % interval:
            raise ValueError(f"steps {steps} must be a whole number of dump_interval {interval}")
        source = self._source(str(config["script"]))
        if not source.is_file():
            raise FileNotFoundError(f"script {source} does not exist; stage the LAMMPS input script with the job")
        run_dir = Path(config["run_dir"])
        run_dir.mkdir(parents=True, exist_ok=True)
        copied = []
        for item in str(config.get("data_files") or "").split():
            extra = self._source(item)
            if not extra.is_file():
                raise FileNotFoundError(f"data file {extra} does not exist; stage it with the job")
            if extra.resolve() != (run_dir / extra.name).resolve():
                shutil.copyfile(extra, run_dir / extra.name)
            copied.append(extra.name)
        target = run_dir / SCRIPT_NAME
        if source.resolve() != target.resolve():
            shutil.copyfile(source, target)
        config["script"] = self.config["script"] = str(target)
        commands = script_commands(target.read_text(encoding="utf-8", errors="replace"))
        if not any(word == "run" for _, word, _ in commands):
            raise ValueError("the script itself has no run command; the package adds its dump before the first one, so keep the runs in the script, not in an included file")
        if any(word in ("dump", "undump", "dump_modify") and args[:1] == [DUMP] for _, word, args in commands):
            raise ValueError(f"the script already names a dump {DUMP!r}; the package adds its own under that name, so rename yours")
        counted = run_steps(commands)
        if counted is not None and counted != steps:
            raise ValueError(f"the script's run commands add up to {counted} steps, not steps = {steps}; set steps to {counted}")

        def first(name: str, default: str | None) -> str | None:
            return next((" ".join(args) for _, word, args in commands if word == name and args), default)

        facts = {
            "script": str(target),
            "data_files": copied,
            "units": first("units", "lj"),
            "atom_style": first("atom_style", "atomic"),
            "pair_style": first("pair_style", None),
            "timestep": first("timestep", None),
            "runs": [" ".join(args) for _, word, args in commands if word == "run"],
            "steps_from_script": counted,
            "nprocs": int(config["nprocs"]),
            "steps": steps,
            "dump_interval": interval,
            "frames_expected": steps // interval + 1,
        }
        (run_dir / CASE_NAME).write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")

    def clio_executable(self) -> str:
        """``lmp``, else the one LAMMPS build named ``lmp_<machine>`` on the install's PATH."""
        path = (self.mod_env or {}).get("PATH") or os.environ.get("PATH", "")
        if shutil.which(self.clio_program, path=path):
            return self.clio_program
        for folder in path.split(os.pathsep):
            if not folder or not os.path.isdir(folder):
                continue
            runnable = [item for item in sorted(Path(folder).glob(f"{self.clio_program}_*")) if os.access(item, os.X_OK)]
            if runnable:
                return str(runnable[0])
        return self.clio_program

    def _write_run_script(self, run_dir: Path) -> Path:
        """in.lammps with the clio dump inserted before its first run, as clio-run.lammps."""
        text = (run_dir / SCRIPT_NAME).read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        first_run = next(index for index, word, _ in script_commands(text) if word == "run")
        interval = int(self.config["dump_interval"])
        dump = [
            "# clio-jarvis: the frames of the live view",
            f"dump {DUMP} all custom {interval} {DUMPS}/dump.*.txt id type x y z vx vy vz",
            f"dump_modify {DUMP} sort id time yes first yes",
        ]
        target = run_dir / RUN_SCRIPT_NAME
        target.write_text("\n".join([*lines[:first_run], *dump, *lines[first_run:]]) + "\n", encoding="utf-8")
        return target

    def _run_outputs(self, run_dir: Path) -> list[Path]:
        return [run_dir / DUMPS, run_dir / FRAMES, run_dir / RESULT_NAME, run_dir / LOG_NAME, run_dir / RUN_SCRIPT_NAME]

    def _remove_outputs(self, run_dir: Path) -> None:
        for path in self._run_outputs(run_dir):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()

    def start(self) -> None:
        self._clio_ensure_configured(prepare=True)
        run_dir = Path(self.config["run_dir"])
        # A rerun starts a fresh series; a viewer must not see the last run's frames.
        self._remove_outputs(run_dir)
        (run_dir / DUMPS).mkdir(parents=True)
        (run_dir / FRAMES).mkdir(parents=True)
        self._write_run_script(run_dir)
        total = int(self.config["steps"]) // int(self.config["dump_interval"])
        publisher = FramePublisher(self.runtime_line_callback(), run_dir, total)
        command = " ".join([shlex.quote(self.clio_executable()), "-in", RUN_SCRIPT_NAME, "-log", LOG_NAME])
        began = time.monotonic()
        publisher.start()
        try:
            codes = self._clio_mpi(command, cwd=str(run_dir), line_callback=publisher, check=False)
        finally:
            publisher.finish()
        try:
            result = self._verdict(run_dir, publisher, codes, time.monotonic() - began)
        finally:
            publisher.release()
        summary = {key: result[key] for key in ("status", "cause", "frames_written", "frames_expected")}
        print(f"clio-lammps result {json.dumps(summary)}", flush=True)
        if result["status"] != "ok":
            raise RuntimeError(f"lammps failed: {result['cause']}; see the job's output and log.lammps")

    def _verdict(self, run_dir: Path, publisher: FramePublisher, codes: dict[str, int], seconds: float) -> dict[str, Any]:
        steps, interval = int(self.config["steps"]), int(self.config["dump_interval"])
        written = publisher.published
        # The first frame is the first run's start, plus one per interval: steps / interval more.
        expected = steps // interval + 1
        failures = {host: code for host, code in codes.items() if code != 0}
        cause = None
        if failures:
            cause = f"lmp exited {failures}"
        elif len(written) < expected:
            cause = f"{len(written)} of {expected} frames written"
        result = {
            "schema": RESULT_SCHEMA,
            "status": "ok" if cause is None else "failed",
            "cause": cause,
            "frames_written": len(written),
            "frames_expected": expected,
            "frames_skipped": publisher.skipped,
            "first_timestep": written[0] if written else None,
            "last_timestep": written[-1] if written else None,
            "atoms": publisher.atoms,
            "last_loop": publisher.loop or None,
            "performance": publisher.performance,
            "wall_seconds": round(seconds, 1),
            "nprocs": int(self.config["nprocs"]),
            "return_codes": codes,
        }
        (run_dir / RESULT_NAME).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return result

    def stop(self) -> None:
        """LAMMPS runs its script to the end."""

    def clean(self) -> None:
        self._clio_ensure_configured(prepare=False)
        self._remove_outputs(Path(self.config["run_dir"]))
