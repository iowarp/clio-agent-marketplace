"""Xcompact3d (Incompact3d v5.0) as a clio-jarvis package (RL40).

With ``geometry`` set to an STL file, the case is flow along +x past that body,
immersed through the immersed boundary method (see ``body.py``). With
``geometry`` empty, it is the Taylor-Green vortex at Re 1600 from the
Incompact3d examples. The run directory gets ``input.i3d``,
``adios2_config.xml`` (BP5), ``clio-vtk.xml`` and ``clio-case.json``. The
software comes from the ``clio.xcompact3d`` Spack recipe in the repository's
``spack/`` directory, which ``jarvis ppl install`` plans from the contract's
install query. Its ``+clio`` variant makes the solver define ``vtk.xml`` from
``clio-vtk.xml`` and put the simulation time in every snapshot, so ParaView's
ADIOS2VTXReader follows ``data.bp5`` while it grows, and reads the body mask
and writes it as ``ep``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import threading
from pathlib import Path
from typing import Any

from clio_jarvis._contract.base import ClioApplication

CONFIG_DIR = Path(__file__).resolve().parent / "config"
#: Seconds between pushes of the snapshots to the file server while the run goes.
FLUSH_SECONDS = 1.0
BODY_STL = "body-input.stl"

#: Point fields the TGV case writes in each snapshot.
TGV_ARRAYS = ("ux", "uy", "uz", "pp", "vort", "critq")
#: A step interval Incompact3d never reaches: what "none" means for icheckpoint and initstat.
NEVER = 100000000


def _every(value: Any) -> int:
    """A positive step count as given; 0 or empty as :data:`NEVER`."""
    return int(value) if value not in (None, "") and int(value) > 0 else NEVER


def set_i3d(text: str, name: str, value: Any) -> str:
    """Set ``name = value`` in an i3d namelist and keep the line's comment."""
    pattern = re.compile(rf"^(\s*{re.escape(name)}\s*=\s*)([^!\n]*?)(\s*(?:!.*)?)$", re.MULTILINE)
    text, count = pattern.subn(lambda m: f"{m.group(1)}{value}{m.group(3)}", text, count=1)
    if count != 1:
        raise ValueError(f"input template has no {name!r} entry")
    return text


def i3d_value(text: str, name: str) -> str:
    match = re.search(rf"^\s*{re.escape(name)}\s*=\s*([^!\n]+)", text, re.MULTILINE)
    if match is None:
        raise ValueError(f"input template has no {name!r} entry")
    return match.group(1).strip()


def vtk_xml(n: tuple[int, int, int], spacing: tuple[float, float, float], arrays: tuple[str, ...]) -> str:
    """The ``vtk.xml`` attribute: point data on an image grid, x fastest.

    The snapshot arrays are Fortran ordered, which the VTX reader takes in
    reverse, so the extent lists z, y, x while the spacing stays x, y, z.
    """
    extent = " ".join(f"0 {count - 1}" for count in reversed(n))
    data_arrays = "\n".join(f'        <DataArray Name="{name}" />' for name in arrays)
    return (
        '<?xml version="1.0"?>\n'
        '<VTKFile type="ImageData" version="0.1" byte_order="LittleEndian">\n'
        f'  <ImageData WholeExtent="{extent}" Origin="0 0 0" '
        f'Spacing="{spacing[0]!r} {spacing[1]!r} {spacing[2]!r}">\n'
        f'    <Piece Extent="{extent}">\n'
        f'      <PointData Scalars="{arrays[0]}">\n'
        f"{data_arrays}\n"
        '        <DataArray Name="TIME">time</DataArray>\n'
        "      </PointData>\n"
        "    </Piece>\n"
        "  </ImageData>\n"
        "</VTKFile>\n"
    )


class Xcompact3d(ClioApplication):
    """Incompressible Navier-Stokes DNS with a growing BP5 snapshot series."""

    clio_program = "xcompact3d"
    clio_probe_arguments = None
    clio_capabilities = ("mpi_execution", "adios2_bp5", "xcompact3d")

    def _configure_menu(self) -> list[dict[str, Any]]:
        return [
            {"name": "nprocs", "msg": "MPI processes; they split the grid into a 2D pencil grid p_row x p_col (see the contract's sizing)", "type": int, "default": 4},
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
                "name": "geometry",
                "msg": (
                    "STL file of the body to put in the flow (binary or ASCII, a closed solid, any "
                    "units); a relative path is from the directory jarvis runs in, and {pkg_dir} "
                    "names this package. Empty means the Taylor-Green vortex case with no body"
                ),
                "type": str,
                "default": "",
            },
            {
                "name": "inflow",
                "msg": "Inflow speed U along +x, in body lengths per unit time (body case)",
                "type": float,
                "default": 1.0,
            },
            {
                "name": "angle",
                "msg": "Angle of attack in degrees, nose up: the body turns about z before it meets the +x flow (body case)",
                "type": float,
                "default": 0.0,
            },
            {
                "name": "resolution",
                "msg": (
                    "Grid points per body length L, so h = 1 / resolution (body case); 16 shows the wake, "
                    "24 to 48 gives forces worth quoting with 6 or more points across the body's thickness, "
                    "and the cost grows with its cube (its square for a periodic span)"
                ),
                "type": int,
                "default": 24,
            },
            {
                "name": "reference_length",
                "msg": "Body length L in STL units; 0 means the STL's extent along x. Set it to the chord for a part already pitched in CAD (body case)",
                "type": float,
                "default": 0.0,
            },
            {
                "name": "span",
                "msg": (
                    "periodic for a section extruded along z (a wing section, a cylinder) run as a "
                    "thin periodic slab with max(8, span x resolution / 2) points across the span, free "
                    "for a whole 3D body with flow round its ends, auto to tell from the STL (body case)"
                ),
                "type": str,
                "default": "auto",
                "choices": ["auto", "periodic", "free"],
            },
            {"name": "upstream", "msg": "Domain length ahead of the body, in body lengths (body case)", "type": float, "default": 3.0},
            {"name": "downstream", "msg": "Domain length behind the body for the wake, in body lengths (body case)", "type": float, "default": 10.0},
            {"name": "lateral", "msg": "Domain margin on each side of the body across the flow, in body lengths (body case)", "type": float, "default": 3.0},
            {
                "name": "n",
                "msg": "Grid points per side, nx = ny = nz: 33, 65, 129 or 257 (Taylor-Green case only; the body case ignores it and sizes its grid from resolution)",
                "type": int,
                "default": 65,
            },
            {"name": "ilast", "msg": "Last time step; the simulated time is ilast x dt, and shedding shows after the flow crosses the domain two to three times", "type": int, "default": 2400},
            {"name": "ioutput", "msg": "Time steps between two snapshots; ilast / ioutput snapshots, 50 to 200 for a smooth live view", "type": int, "default": 20},
            {
                "name": "dt",
                "msg": (
                    "Time step. Work it out before submitting: CFL = inflow x dt / h at most 0.2 (aim for "
                    "0.1) and dt x nu x (2 / h^2 + 1 / dz^2) at most 0.0075, with nu = inflow / re; take "
                    "the smaller bound (see the summary). The body case refuses an unstable dt when the "
                    "job starts and names the largest safe value"
                ),
                "type": float,
                "default": 0.005,
            },
            {
                "name": "re",
                "msg": "Reynolds number; for the body case U L / nu with L the body length",
                "type": float,
                "default": 1600.0,
            },
            {
                "name": "input_template",
                "msg": "Incompact3d input file to start from; empty means the TGV Re1600 example",
                "type": str,
                "default": "",
            },
            {
                "name": "run_dir",
                "msg": "Folder on the site for the run: input.i3d, clio-case.json, body.stl, forces.dat and the growing snapshot output data.bp5. Set it to a folder you can read, such as the one holding the geometry, to open data.bp5 in ParaView while the run goes; empty means a folder inside the job's own directory",
                "type": str,
                "default": "",
            },
            {
                "name": "icheckpoint",
                "msg": (
                    "Time steps between restart files (checkpoint.bp5) and statistics writes (statistics.bp5); "
                    "0 means none. Restart files hold the whole flow state, so keep this well above ioutput"
                ),
                "type": int,
                "default": 0,
            },
            {
                "name": "initstat",
                "msg": (
                    "Time step from which the run averages statistics, written to statistics.bp5 every "
                    "icheckpoint steps; 0 means no statistics"
                ),
                "type": int,
                "default": 0,
            },
            {"name": "walltime", "msg": "Wall-time limit in seconds, about nx x ny x nz x ilast / (site throughput x nprocs) plus a margin (see the contract's sizing); absent means no limit", "type": int, "default": None, "required": False},
            {"name": "queue", "msg": "Batch queue; empty means the site default", "type": str, "default": ""},
        ]

    def _clio_prepare(self, config: dict[str, Any]) -> None:
        run_dir = Path(config["run_dir"])
        (run_dir / "data").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CONFIG_DIR / "adios2_config.xml", run_dir / "adios2_config.xml")
        if config.get("geometry"):
            self._prepare_body(config, run_dir)
        else:
            self._prepare_tgv(config, run_dir)

    def _prepare_body(self, config: dict[str, Any], run_dir: Path) -> None:
        from clio_jarvis.xcompact3d import body

        source = Path(str(config["geometry"]).replace("{pkg_dir}", str(self.pkg_dir))).expanduser()
        source = source if source.is_absolute() else Path(os.getcwd()) / source
        if not source.is_file():
            raise FileNotFoundError(f"geometry {source} does not exist; stage the STL with the job")
        # Keep the STL in the run directory, so a re-configure from another directory still finds it.
        target = run_dir / BODY_STL
        if source.resolve() != target.resolve():
            shutil.copyfile(source, target)
        config["geometry"] = self.config["geometry"] = str(target)

        inflow, re_, dt = float(config["inflow"]), float(config["re"]), float(config["dt"])
        ilast, ioutput = int(config["ilast"]), int(config["ioutput"])
        case = body.plan_body(
            target,
            resolution=int(config["resolution"]),
            angle=float(config["angle"]),
            reference_length=float(config["reference_length"]),
            span=str(config["span"]),
            upstream=float(config["upstream"]),
            downstream=float(config["downstream"]),
            lateral=float(config["lateral"]),
            nprocs=int(config["nprocs"]),
            inflow=inflow,
            re=re_,
            dt=dt,
        )
        (run_dir / "input.i3d").write_text(
            body.input_i3d(
                case,
                inflow=inflow,
                re=re_,
                dt=dt,
                ilast=ilast,
                ioutput=ioutput,
                icheckpoint=_every(config.get("icheckpoint")),
                initstat=_every(config.get("initstat")),
            ),
            encoding="utf-8",
        )
        case.mask.write(run_dir)
        body.write_stl(case.body, run_dir / "body.stl")
        (run_dir / "clio-vtk.xml").write_text(vtk_xml(case.grid, case.spacing, body.BODY_ARRAYS), encoding="utf-8")
        self._write_case(
            run_dir,
            {
                "case": "body",
                "geometry": {"file": BODY_STL, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()},
                "span": case.span,
                "grid": list(case.grid),
                "domain": list(case.domain),
                "spacing": list(case.spacing),
                "decomposition": list(case.decomposition),
                "inflow": inflow,
                "reynolds": re_,
                "angle_deg": float(config["angle"]),
                "time_end": ilast * dt,
                "flow_throughs": ilast * dt * inflow / case.domain[0],
                "body_stl_in_solver_frame": "body.stl",
                "forces": "forces.dat: time, drag, lift from a control volume round the body; for a periodic span these are coefficients on L per unit span for U = 1 (divide by U squared otherwise)",
                **case.facts,
            },
        )

    def _prepare_tgv(self, config: dict[str, Any], run_dir: Path) -> None:
        text = Path(config["input_template"]).read_text(encoding="utf-8")
        n = int(config["n"])
        for name, value in (
            ("nx", n),
            ("ny", n),
            ("nz", n),
            ("ilast", int(config["ilast"])),
            ("ioutput", int(config["ioutput"])),
            ("icheckpoint", _every(config.get("icheckpoint"))),
            ("dt", repr(float(config["dt"]))),
            ("re", repr(float(config["re"]))),
        ):
            text = set_i3d(text, name, value)
        # The example has no initstat line; Incompact3d's default would average from step 1.
        text = re.sub(
            r"^(\s*nstat\s*=.*)$",
            lambda m: f"{m.group(1)}\ninitstat = {_every(config.get('initstat'))}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        (run_dir / "input.i3d").write_text(text, encoding="utf-8")

        spacing = []
        for length, ncl in (("xlx", "nclx1"), ("yly", "ncly1"), ("zlz", "nclz1")):
            size = float(i3d_value(text, length))
            periodic = int(float(i3d_value(text, ncl))) == 0
            spacing.append(size / n if periodic else size / (n - 1))
        (run_dir / "clio-vtk.xml").write_text(
            vtk_xml((n, n, n), (spacing[0], spacing[1], spacing[2]), TGV_ARRAYS), encoding="utf-8"
        )
        self._write_case(run_dir, {"case": "taylor-green", "grid": [n, n, n], "spacing": spacing, "reynolds": float(config["re"])})

    @staticmethod
    def _write_case(run_dir: Path, facts: dict[str, Any]) -> None:
        (run_dir / "clio-case.json").write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")

    def _output(self) -> Path:
        return Path(self.config["run_dir"]) / "data.bp5"

    def _run_outputs(self) -> list[Path]:
        """What a run writes into run_dir: the snapshots, statistics and restart files."""
        run_dir = Path(self.config["run_dir"])
        return [self._output()] + [run_dir / name for name in ("statistics.bp5", "checkpoint.bp5", "checkpoint.old", "restart.info")]

    def start(self) -> None:
        self._clio_ensure_configured(prepare=True)
        run_dir = Path(self.config["run_dir"])
        # A rerun starts afresh (irestart = 0); a viewer must not see the last run's steps.
        for path in self._run_outputs():
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                path.unlink()
        command = f"{shlex.quote(self.clio_executable())} input.i3d"
        done = threading.Event()
        flusher = threading.Thread(target=_flush_output, args=(self._output(), done), daemon=True)
        flusher.start()
        try:
            self._clio_mpi(command, cwd=str(run_dir))
        finally:
            done.set()
            flusher.join(timeout=10)

    def stop(self) -> None:
        """Xcompact3d runs to its last time step."""

    def clean(self) -> None:
        self._clio_ensure_configured(prepare=False)
        shutil.rmtree(self._output(), ignore_errors=True)


def _flush_output(output: Path, done: threading.Event) -> None:
    """Push the run's BP5 snapshots to the file server every ``FLUSH_SECONDS``.

    ADIOS2 does not sync, so on a shared file system the compute node holds
    new snapshots in its page cache and writes them back in bursts (Linux's
    default is 30 s). A viewer on another machine would see the run jump
    tens of steps at a time. Syncing the data files before the metadata and
    the index keeps every step the index names on the server. Only this
    run's output folder is touched, and a sync of unchanged files costs
    nothing. On several nodes this flushes only the subfiles written here.
    """
    while not done.wait(FLUSH_SECONDS):
        if not output.is_dir():
            continue
        names = sorted(p.name for p in output.glob("data.*"))
        for name in names + ["md.0", "mmd.0", "md.idx"]:
            try:
                fd = os.open(output / name, os.O_RDONLY)
            except OSError:
                continue
            try:
                os.fsync(fd)
            except OSError:
                pass
            finally:
                os.close(fd)
