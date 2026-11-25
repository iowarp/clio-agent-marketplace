"""GROMACS (biomolecular molecular dynamics) as a clio-jarvis package.

The case is GROMACS's own files: ``mdp``, the run parameters of the run the
person watches, and ``files``, everything else the case reads (a structure
such as a .pdb or .gro, a topology .top and its .itp files, the .mdp files of
earlier stages, an index). Configure keeps them as given in run_dir/case, and
each start copies them into the run directory afresh, since stages such as
solvate and genion edit the topology in place. ``prepare``
then runs the stages before the watched run, one gmx command per line, as
GROMACS's own tools would be run by hand (``pdb2gmx``, ``editconf``,
``solvate``, ``grompp``, ``genion``, ``mdrun`` for minimisation and
equilibration). A line may end in ``<<< answers``: the answers go to the
tool's prompts, one per line (``genion ... <<< SOL``). Only gmx tools run;
mdrun stages run on all the ranks, the other tools on one.

The watched run is ``grompp -f md.mdp -c structure -p topology`` and
``mdrun -deffnm md``. The package writes md.mdp from ``mdp`` with ``nsteps``
set and ``nstxout`` (and ``nstvout``) set to ``frame_interval``. GROMACS
flushes the full-precision trajectory md.trr after each frame, so a publisher
thread reads each whole frame from it while mdrun runs, writes it as a VTK
PolyData file ``frames/frame_<step>.vtp`` (atoms as points with their
element, residue and velocity, the simulated time as TimeValue) and prints
``clio-gromacs frame I of M``, which the contract's progress pattern counts.

The software is a Spack ``gromacs`` with MPI (``gmx_mpi``). MPI, the
launcher, the nodes and the ranks per node come from JARVIS and the site's
resource graph through the launch, never from this package.
"""

from __future__ import annotations

import json
import math
import os
import re
import shlex
import shutil
import struct
import time
from array import array
from collections.abc import Callable
from pathlib import Path
from typing import Any

from clio_jarvis._contract.base import ClioApplication, mpi_safe_env
from clio_jarvis._contract.points import write_points_vtp
from clio_jarvis._contract.publisher import PollingPublisher
from jarvis_cd.shell import Exec, LocalExecInfo, MpiExecInfo

RESULT_SCHEMA = "clio.gromacs-run.v1"
RESULT_NAME = "clio-run-result.json"
CASE_NAME = "clio-case.json"
CASE_DIR = "case"
DEFFNM = "md"
MDP_NAME = "md.mdp"
TRR_NAME = "md.trr"
FRAMES = "frames"
DIGITS = 10
TRR_MAGIC = 1993
#: mdp keys the package sets for the watched run; the person's values of these give way.
_OWN_KEYS = ("nsteps", "nstxout", "nstvout", "nstfout")
_PERFORMANCE = re.compile(r"^Performance:\s+(?P<ns_day>[\d.]+)\s+(?P<hour_ns>[\d.]+)")
_ELEMENTS = {"H": 1, "C": 6, "N": 7, "O": 8, "F": 9, "NA": 11, "MG": 12, "P": 15, "S": 16, "CL": 17, "K": 19, "CA": 20, "ZN": 30}
_SOLVENT = {"SOL", "HOH", "WAT", "TIP3", "TIP4", "SPC", "T3P"}


def mdp_key(key: str) -> str:
    return key.strip().lower().replace("_", "-")


def parse_mdp(text: str) -> dict[str, str]:
    """The ``key = value`` lines of an mdp file, keys normalised (lower case, - for _)."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        if "=" in line:
            key, _, value = line.partition("=")
            values[mdp_key(key)] = value.strip()
    return values


def watched_mdp(text: str, nsteps: int, interval: int, velocities: bool) -> str:
    """The mdp with the package's keys removed from it and set at its end."""
    own = set(_OWN_KEYS)
    kept = [raw for raw in text.splitlines() if mdp_key(raw.split(";", 1)[0].partition("=")[0]) not in own or "=" not in raw.split(";", 1)[0]]
    settings = {"nsteps": nsteps, "nstxout": interval, "nstvout": interval if velocities else 0, "nstfout": 0}
    return "\n".join([*kept, "", "; clio-jarvis: the length and the frames of the live view", *(f"{k:<10} = {v}" for k, v in settings.items())]) + "\n"


def prepare_lines(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        items = [str(item) for item in value]
    else:
        items = str(value or "").splitlines()
    return [item.strip() for item in items if item.strip() and not item.strip().startswith("#")]


def parse_prepare(line: str) -> tuple[list[str], str | None]:
    """One prepare line as (gmx arguments, answers for stdin or None)."""
    command, marker, answers = line.partition("<<<")
    args = shlex.split(command)
    if args and args[0] in ("gmx", "gmx_mpi", "gmx_d", "gmx_mpi_d"):
        args = args[1:]
    if not args or not re.fullmatch(r"[a-z][a-z0-9_-]*", args[0]):
        raise ValueError(f"prepare line {line!r} is not a gmx tool and its arguments")
    stdin = "\n".join(shlex.split(answers)) + "\n" if marker else None
    return args, stdin


def element_of(atom: str, residue: str) -> int:
    """The atomic number an atom name suggests; 0 when it suggests none."""
    letters = re.sub(r"[^A-Z]", "", atom.upper())
    ion = re.sub(r"[^A-Z]", "", residue.upper())
    # An ion's residue is its element (NA, CL, CA...); in a protein, CA is the alpha carbon.
    if len(letters) >= 2 and letters[:2] in _ELEMENTS and ion.startswith(letters[:2]):
        return _ELEMENTS[letters[:2]]
    return _ELEMENTS.get(letters[:1], 0)


def read_atoms(path: Path) -> list[tuple[int, str, str]] | None:
    """(residue number, residue name, atom name) per atom of a .gro or .pdb file, or None."""
    try:
        lines = path.read_text(encoding="ascii", errors="replace").splitlines()
    except OSError:
        return None
    atoms: list[tuple[int, str, str]] = []
    try:
        if path.suffix.lower() == ".gro":
            count = int(lines[1])
            for row in lines[2 : 2 + count]:
                atoms.append((int(row[0:5]), row[5:10].strip(), row[10:15].strip()))
        elif path.suffix.lower() in (".pdb", ".ent"):
            for row in lines:
                if row.startswith(("ATOM", "HETATM")):
                    atoms.append((int(row[22:26]), row[17:21].strip(), row[12:16].strip()))
                elif row.startswith("ENDMDL"):
                    break
        else:
            return None
    except (ValueError, IndexError):
        return None
    return atoms


class TrrReader:
    """Reads the whole frames GROMACS has appended to a .trr since the last call (XDR, big-endian)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.offset = 0

    def frames(self) -> list[dict[str, Any]]:
        try:
            with self.path.open("rb") as handle:
                handle.seek(self.offset)
                data = handle.read()
        except FileNotFoundError:
            return []
        found = []
        at = 0
        while True:
            frame = self._frame(data, at)
            if frame is None:
                break
            at = frame.pop("end")
            found.append(frame)
        self.offset += at
        return found

    @staticmethod
    def _frame(data: bytes, at: int) -> dict[str, Any] | None:
        if len(data) - at < 12:
            return None
        magic, _ = struct.unpack_from(">ii", data, at)
        if magic != TRR_MAGIC:
            raise ValueError(f"md.trr holds no TRR frame at byte {at}")
        (length,) = struct.unpack_from(">i", data, at + 8)
        at += 12 + 4 * math.ceil(length / 4)
        if len(data) - at < 13 * 4:
            return None
        sizes = struct.unpack_from(">13i", data, at)
        at += 13 * 4
        _ir, _e, box, vir, pres, _top, _sym, x, v, f, natoms, step, _nre = sizes
        if box:
            real = box // 9
        elif x:
            real = x // (natoms * 3)
        elif v:
            real = v // (natoms * 3)
        else:
            real = f // (natoms * 3) if f else 4
        kind = "d" if real == 8 else "f"
        end = at + 2 * real + box + vir + pres + x + v + f
        if len(data) < end:
            return None
        sim_time, _lam = struct.unpack_from(f">2{kind}", data, at)
        at += 2 * real
        frame: dict[str, Any] = {"step": step, "time": sim_time, "natoms": natoms, "end": end}
        if box:
            frame["box"] = list(struct.unpack_from(f">9{kind}", data, at))
        at += box + vir + pres
        if x:
            frame["x"] = struct.unpack_from(f">{natoms * 3}{kind}", data, at)
        at += x
        if v:
            frame["v"] = struct.unpack_from(f">{natoms * 3}{kind}", data, at)
        return frame


def frame_name(step: int) -> str:
    return f"frame_{step:0{DIGITS}d}.vtp"


def frame_to_vtp(frame: dict[str, Any], atoms: list[tuple[int, str, str]] | None, target: Path) -> None:
    count = frame["natoms"]
    arrays: dict[str, tuple[array, int]] = {"atom": (array("i", range(1, count + 1)), 1)}
    if atoms is not None and len(atoms) == count:
        arrays["element"] = (array("i", (element_of(name, residue) for _, residue, name in atoms)), 1)
        arrays["residue"] = (array("i", (number for number, _, _ in atoms)), 1)
        arrays["solvent"] = (array("i", (1 if residue.upper() in _SOLVENT else 0 for _, residue, _ in atoms)), 1)
    if "v" in frame:
        velocity = frame["v"]
        arrays["velocity"] = (array("f", velocity), 3)
        speeds = (math.sqrt(velocity[i] ** 2 + velocity[i + 1] ** 2 + velocity[i + 2] ** 2) for i in range(0, len(velocity), 3))
        arrays["speed"] = (array("f", speeds), 1)
    write_points_vtp(
        target,
        frame["x"],
        arrays,
        time=frame["time"],
        field_arrays={"step": [frame["step"]], "box": frame.get("box", [])},
    )


class TrrPublisher(PollingPublisher):
    """Turns each whole frame of md.trr into a .vtp in frames/ while mdrun runs."""

    def __init__(self, inner: Callable[[str, str], None] | None, run_dir: Path, total: int, atoms: list[tuple[int, str, str]] | None) -> None:
        super().__init__(inner)
        self.reader = TrrReader(run_dir / TRR_NAME)
        self.frames = run_dir / FRAMES
        self.total = total
        self.atoms = atoms
        self.published: list[int] = []
        self.natoms: int | None = None
        self.last_time: float | None = None
        self.error: str | None = None
        self._began = time.monotonic()

    def poll(self, final: bool) -> None:
        with self.lock:
            if self.error is not None:
                return
            try:
                frames = self.reader.frames()
            except ValueError as error:
                self.error = str(error)
                self.emit(f"clio-gromacs {error}; frames stop here")
                return
            for frame in frames:
                if "x" not in frame:
                    continue
                frame_to_vtp(frame, self.atoms, self.frames / frame_name(frame["step"]))
                self.published.append(frame["step"])
                self.natoms, self.last_time = frame["natoms"], frame["time"]
                self.emit(
                    f"clio-gromacs frame {len(self.published) - 1} of {self.total} {frame_name(frame['step'])} "
                    f"step {frame['step']} time {frame['time']:.4f} ps atoms {frame['natoms']} "
                    f"wall {time.monotonic() - self._began:.1f}"
                )


class Gromacs(ClioApplication):
    """GROMACS on the person's own mdp, structure and topology, with a growing series of frames."""

    clio_program = "gmx_mpi"
    clio_probe_arguments = None
    clio_capabilities = ("mpi_execution", "gromacs", "particle_frames")

    def _configure_menu(self) -> list[dict[str, Any]]:
        return [
            {"name": "nprocs", "msg": "MPI processes of each mdrun; GROMACS splits the box over them by domain decomposition (see the contract's sizing)", "type": int, "default": 8},
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
            {"name": "ntomp", "msg": "OpenMP threads per MPI process of each mdrun (mdrun -ntomp); ppn x ntomp should not pass the node's cores", "type": int, "default": 1},
            {
                "name": "mdp",
                "msg": (
                    "GROMACS run parameter file (.mdp, the solver's own key = value format) of the watched run: "
                    "integrator, dt, cutoffs, electrostatics, thermostat and barostat, constraints. nsteps, nstxout, "
                    "nstvout and nstfout are set by the package. A relative path is from the directory jarvis runs "
                    "in, and {pkg_dir} names this package"
                ),
                "type": str,
                "default": "",
            },
            {
                "name": "files",
                "msg": "The case's other files (structure .pdb or .gro, topology .top and .itp, the .mdp files of the prepare stages, an index .ndx), space separated; each is copied into run_dir under its own name",
                "type": str,
                "default": "",
            },
            {
                "name": "prepare",
                "msg": (
                    "Stages before the watched run, one gmx command per line without the gmx, run in run_dir in order "
                    "(pdb2gmx, editconf, solvate, grompp, genion, and mdrun for minimisation and equilibration). "
                    "End a line with <<< and the answers to the tool's prompts, such as genion ... <<< SOL. Empty means none"
                ),
                "type": str,
                "default": "",
            },
            {"name": "structure", "msg": "Starting structure of the watched run in run_dir (grompp -c), a file of files or one prepare writes", "type": str, "default": "conf.gro"},
            {"name": "topology", "msg": "Topology of the watched run in run_dir (grompp -p)", "type": str, "default": "topol.top"},
            {"name": "restraints", "msg": "Reference structure for position restraints (grompp -r); empty means none", "type": str, "default": ""},
            {"name": "index", "msg": "Index file in run_dir (grompp -n); empty means none", "type": str, "default": ""},
            {"name": "maxwarn", "msg": "Warnings grompp may pass over (grompp -maxwarn); keep 0 unless the warning is understood", "type": int, "default": 0},
            {"name": "nsteps", "msg": "Steps of the watched run; it replaces the mdp's nsteps", "type": int, "default": 50000},
            {"name": "frame_interval", "msg": "Steps between two frames of the live view (nstxout); nsteps must be a whole number of them", "type": int, "default": 500},
            {"name": "write_velocities", "msg": "Write velocities into each frame too (nstvout), for the speed array", "type": bool, "default": True},
            {"name": "run_dir", "msg": "Run directory; empty means {shared_dir}/run", "type": str, "default": ""},
            {"name": "walltime", "msg": "Wall-time limit in seconds; absent means no limit", "type": int, "default": None, "required": False},
            {"name": "queue", "msg": "Batch queue; empty means the site default", "type": str, "default": ""},
        ]

    def _source(self, value: str) -> Path:
        path = Path(value.replace("{pkg_dir}", str(self.pkg_dir))).expanduser()
        return path if path.is_absolute() else Path(os.getcwd()) / path

    def _copy_in(self, value: str, target: Path, what: str) -> str:
        source = self._source(value)
        if not source.is_file():
            raise FileNotFoundError(f"{what} {source} does not exist; stage it with the job")
        if source.resolve() != (target / source.name).resolve():
            shutil.copyfile(source, target / source.name)
        return source.name

    def _restore_case(self, run_dir: Path) -> None:
        """Put the person's files back in run_dir as given: stages such as solvate and genion edit them in place."""
        for name in str(self.config.get("files") or "").split():
            shutil.copyfile(name, run_dir / Path(name).name)

    def _clio_prepare(self, config: dict[str, Any]) -> None:
        nsteps, interval = int(config["nsteps"]), int(config["frame_interval"])
        if nsteps % interval:
            raise ValueError(f"nsteps {nsteps} must be a whole number of frame_interval {interval}")
        run_dir = Path(config["run_dir"])
        case = run_dir / CASE_DIR
        case.mkdir(parents=True, exist_ok=True)
        mdp = self._copy_in(str(config["mdp"]), case, "mdp")
        if mdp == MDP_NAME:
            raise ValueError(f"name the mdp something other than {MDP_NAME}; the package writes the watched run's {MDP_NAME} from it")
        copied = [self._copy_in(item, case, "file") for item in str(config.get("files") or "").split()]
        if len(set(copied)) != len(copied):
            raise ValueError("two of files share a name; every file lands in run_dir under its own name")
        # The copies in run_dir/case are the case from now on; each start restores them into run_dir.
        config["mdp"] = self.config["mdp"] = str(case / mdp)
        config["files"] = self.config["files"] = " ".join(str(case / name) for name in copied)
        self._restore_case(run_dir)
        stages = [parse_prepare(line) for line in prepare_lines(config.get("prepare"))]
        written_by_stages = {
            args[index + 1]
            for args, _ in stages
            for index, arg in enumerate(args[:-1])
            if arg in ("-o", "-p", "-c", "-deffnm")
        }
        for name in ("structure", "topology", "restraints", "index"):
            value = str(config.get(name) or "")
            if value and "/" in value:
                raise ValueError(f"{name} {value!r} names a file in run_dir, so give its name only")
            if value and not (run_dir / value).is_file() and value not in written_by_stages and not any(value.startswith(stem + ".") for stem in written_by_stages):
                raise FileNotFoundError(f"{name} {value} is neither among files nor written by a prepare stage")
        values = parse_mdp((case / mdp).read_text(encoding="utf-8", errors="replace"))
        dt = float(values.get("dt", "0.001"))
        facts = {
            "mdp": mdp,
            "files": copied,
            "prepare": [" ".join(args) + (" <<< answers" if stdin else "") for args, stdin in stages],
            "integrator": values.get("integrator", "md"),
            "dt_ps": dt,
            "simulated_ps": round(nsteps * dt, 6),
            "replaced": {key: values[key] for key in _OWN_KEYS if key in values},
            "structure": config.get("structure"),
            "topology": config.get("topology"),
            "nprocs": int(config["nprocs"]),
            "ntomp": int(config["ntomp"]),
            "nsteps": nsteps,
            "frame_interval": interval,
            "frames_expected": nsteps // interval + 1,
        }
        (run_dir / CASE_NAME).write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")

    def clio_executable(self) -> str:
        """``gmx_mpi``, else ``gmx`` (a thread-MPI build, one node only) on the install's PATH."""
        path = (self.mod_env or {}).get("PATH") or os.environ.get("PATH", "")
        for program in (self.clio_program, "gmx"):
            if shutil.which(program, path=path):
                return program
        return self.clio_program

    def _env(self) -> dict[str, str]:
        # GROMACS would back an overwritten file up as #name.1#; the stages overwrite on purpose.
        return {**mpi_safe_env(self.mod_env), "GMX_MAXBACKUP": "-1"}

    def _gmx(self, args: list[str], run_dir: Path, stdin: str | None = None, line_callback=None) -> dict[str, int]:
        """One gmx tool: mdrun on all the ranks, any other tool on one."""
        program = self.clio_executable()
        mdrun = args[0] == "mdrun"
        extra = ["-ntomp", str(int(self.config["ntomp"]))] if mdrun and "-ntomp" not in args else []
        callback = line_callback if line_callback is not None else self.runtime_line_callback()
        if program == "gmx":
            if mdrun and not self._clio_runs_here():
                raise RuntimeError("this GROMACS is a thread-MPI build (gmx, no gmx_mpi), which runs on one node only")
            if mdrun and "-ntmpi" not in args:
                extra += ["-ntmpi", str(int(self.config["nprocs"]))]
            info: Any = LocalExecInfo(env=self._env(), cwd=str(run_dir), stdin=stdin, line_callback=callback)
        else:
            ranks = int(self.config["nprocs"]) if mdrun else 1
            info = MpiExecInfo(
                nprocs=ranks,
                ppn=self.clio_ppn() if mdrun else 1,
                hostfile=self.hostfile,
                env=self._env(),
                cwd=str(run_dir),
                stdin=stdin,
                line_callback=callback,
            )
        command = shlex.join([program, *args, *extra])
        print(f"clio-gromacs running {command}", flush=True)
        return dict(Exec(command, info).run().exit_code)

    def _run_outputs(self, run_dir: Path) -> list[Path]:
        names = [FRAMES, RESULT_NAME, MDP_NAME, "mdout.mdp", *(f"{DEFFNM}.{ext}" for ext in ("tpr", "trr", "log", "edr", "gro", "cpt", "xtc"))]
        return [run_dir / name for name in names] + [run_dir / f"{DEFFNM}_prev.cpt"]

    def _remove_outputs(self, run_dir: Path) -> None:
        for path in self._run_outputs(run_dir):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()

    def _failed(self, codes: dict[str, int]) -> dict[str, int]:
        return {host: code for host, code in codes.items() if code != 0}

    def start(self) -> None:
        self._clio_ensure_configured(prepare=True)
        run_dir = Path(self.config["run_dir"])
        # A rerun starts a fresh series; a viewer must not see the last run's frames.
        self._remove_outputs(run_dir)
        self._restore_case(run_dir)
        (run_dir / FRAMES).mkdir(parents=True)
        began = time.monotonic()
        nsteps, interval = int(self.config["nsteps"]), int(self.config["frame_interval"])
        # One publisher sees every stage's lines and holds the providers' end until the verdict is written.
        publisher = TrrPublisher(self.runtime_line_callback(), run_dir, nsteps // interval, None)
        codes: dict[str, int] = {}
        stage_failure = None
        try:
            for number, line in enumerate(prepare_lines(self.config.get("prepare")), start=1):
                args, stdin = parse_prepare(line)
                failures = self._failed(self._gmx(args, run_dir, stdin, publisher))
                if failures:
                    stage_failure = f"prepare stage {number} ({args[0]}) exited {failures}"
                    break
            if stage_failure is None:
                text = Path(self.config["mdp"]).read_text(encoding="utf-8", errors="replace")
                velocities = bool(self.config.get("write_velocities", True))
                (run_dir / MDP_NAME).write_text(watched_mdp(text, nsteps, interval, velocities), encoding="utf-8")
                failures = self._failed(self._gmx(self._grompp(), run_dir, None, publisher))
                if failures:
                    stage_failure = f"grompp of the watched run exited {failures}"
            if stage_failure is None:
                publisher.atoms = read_atoms(run_dir / str(self.config["structure"]))
                publisher.start()
                try:
                    codes = self._gmx(["mdrun", "-deffnm", DEFFNM], run_dir, None, publisher)
                finally:
                    publisher.finish()
            result = self._verdict(run_dir, publisher, codes, stage_failure, time.monotonic() - began)
            if result["status"] != "ok":
                publisher.finalize_process(1)
        finally:
            publisher.release()
        summary = {key: result[key] for key in ("status", "cause", "frames_written", "frames_expected")}
        print(f"clio-gromacs result {json.dumps(summary)}", flush=True)
        if result["status"] != "ok":
            raise RuntimeError(f"gromacs failed: {result['cause']}; see the job's output and md.log")

    def _grompp(self) -> list[str]:
        args = ["grompp", "-f", MDP_NAME, "-c", str(self.config["structure"]), "-p", str(self.config["topology"])]
        args += ["-o", f"{DEFFNM}.tpr", "-maxwarn", str(int(self.config["maxwarn"]))]
        if self.config.get("restraints"):
            args += ["-r", str(self.config["restraints"])]
        if self.config.get("index"):
            args += ["-n", str(self.config["index"])]
        return args

    def _verdict(self, run_dir: Path, publisher: TrrPublisher, codes: dict[str, int], stage_failure: str | None, seconds: float) -> dict[str, Any]:
        nsteps, interval = int(self.config["nsteps"]), int(self.config["frame_interval"])
        expected = nsteps // interval + 1
        written = publisher.published
        log = run_dir / f"{DEFFNM}.log"
        log_text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
        performance = next((found for row in log_text.splitlines() if (found := _PERFORMANCE.match(row.strip()))), None)
        failures = self._failed(codes)
        cause = stage_failure
        if cause is None and failures:
            cause = f"mdrun exited {failures}"
        elif cause is None and publisher.error:
            cause = publisher.error
        elif cause is None and len(written) < expected:
            cause = f"{len(written)} of {expected} frames written"
        elif cause is None and "Finished mdrun" not in log_text:
            cause = "md.log does not say Finished mdrun"
        result = {
            "schema": RESULT_SCHEMA,
            "status": "ok" if cause is None else "failed",
            "cause": cause,
            "frames_written": len(written),
            "frames_expected": expected,
            "first_step": written[0] if written else None,
            "last_step": written[-1] if written else None,
            "last_time_ps": publisher.last_time,
            "atoms": publisher.natoms,
            "ns_per_day": float(performance.group("ns_day")) if performance else None,
            "hours_per_ns": float(performance.group("hour_ns")) if performance else None,
            "wall_seconds": round(seconds, 1),
            "nprocs": int(self.config["nprocs"]),
            "ntomp": int(self.config["ntomp"]),
            "return_codes": codes,
        }
        (run_dir / RESULT_NAME).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return result

    def stop(self) -> None:
        """mdrun runs to nsteps."""

    def clean(self) -> None:
        self._clio_ensure_configured(prepare=False)
        self._remove_outputs(Path(self.config["run_dir"]))

