"""ADIOS2 Gray-Scott as a clio-jarvis package (RL40).

The run directory gets ``settings.json`` and ``adios2.xml``. The solver runs
under MPI there and writes ``gs.bp`` with a ``vtk.xml`` attribute, so ParaView's
ADIOS2VTXReader opens it as image data and sees each new step as it lands. The
software comes from the ``clio.gray-scott`` Spack recipe in the repository's
``spack/`` directory, whose ``+clio`` variant adds that attribute and the
simulation time; ``jarvis ppl install`` plans it from the contract's install
query.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from clio_jarvis._contract.base import ClioApplication

#: Seconds between syncs of gs.bp on each node with solver ranks.
FLUSH_SECONDS = 1.0

CONFIG_DIR = Path(__file__).resolve().parent / "config"


class GrayScott(ClioApplication):
    """Gray-Scott reaction-diffusion with a growing BP5 output."""

    clio_program = "adios2_simulations_gray-scott"
    clio_probe_arguments = None
    clio_capabilities = ("mpi_execution", "adios2_bp5", "gray_scott")

    def _configure_menu(self) -> list[dict[str, Any]]:
        return [
            {"name": "nprocs", "msg": "MPI processes; they split the grid into a 3D block grid (see the contract's sizing)", "type": int, "default": 4},
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
            {"name": "L", "msg": "Grid cells per side (the grid is L x L x L)", "type": int, "default": 128},
            {"name": "steps", "msg": "Simulation steps", "type": int, "default": 15000},
            {"name": "plotgap", "msg": "Simulation steps between two output steps", "type": int, "default": 150},
            {"name": "F", "msg": "Feed rate", "type": float, "default": 0.01},
            {"name": "k", "msg": "Kill rate", "type": float, "default": 0.05},
            {"name": "Du", "msg": "Diffusion rate of U", "type": float, "default": 0.2},
            {"name": "Dv", "msg": "Diffusion rate of V", "type": float, "default": 0.1},
            {"name": "dt", "msg": "Time step", "type": float, "default": 2.0},
            {"name": "noise", "msg": "Amplitude of the initial noise", "type": float, "default": 1e-7},
            {
                "name": "run_dir",
                "msg": "Run directory; empty means {shared_dir}/run",
                "type": str,
                "default": "",
            },
            {
                "name": "checkpoint_freq",
                "msg": "Simulation steps between checkpoints written to ckpt.bp; 0 means none",
                "type": int,
                "default": 0,
            },
            {"name": "walltime", "msg": "Wall-time limit in seconds; absent means no limit", "type": int, "default": None, "required": False},
            {"name": "queue", "msg": "Batch queue; empty means the site default", "type": str, "default": ""},
        ]

    def _clio_prepare(self, config: dict[str, Any]) -> None:
        run_dir = Path(config["run_dir"])
        run_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CONFIG_DIR / "adios2.xml", run_dir / "adios2.xml")
        settings = {
            "L": config["L"],
            "Du": config["Du"],
            "Dv": config["Dv"],
            "F": config["F"],
            "k": config["k"],
            "dt": config["dt"],
            "plotgap": config["plotgap"],
            "steps": config["steps"],
            "noise": config["noise"],
            "output": str(run_dir / "gs.bp"),
            "checkpoint": bool(config.get("checkpoint_freq")),
            "checkpoint_freq": int(config.get("checkpoint_freq") or 0) or 100000000,
            "checkpoint_output": str(run_dir / "ckpt.bp"),
            "restart": False,
            "restart_input": str(run_dir / "ckpt.bp"),
            "adios_config": str(run_dir / "adios2.xml"),
            "adios_span": False,
            "adios_memory_selection": False,
            "mesh_type": "image",
        }
        (run_dir / "settings.json").write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")

    def _output(self) -> Path:
        return Path(self.config["run_dir"]) / "gs.bp"

    def start(self) -> None:
        self._clio_ensure_configured(prepare=True)
        run_dir = Path(self.config["run_dir"])
        # A rerun starts a fresh series; a viewer must not see the last run's steps.
        shutil.rmtree(self._output(), ignore_errors=True)
        shutil.rmtree(run_dir / "ckpt.bp", ignore_errors=True)
        from clio_jarvis._contract import flushwrap
        from clio_jarvis._contract.files import revealing

        # ADIOS2 does not sync: without a flusher where the ranks write, a viewer
        # on another node sees gs.bp jump by the page cache's writeback interval.
        command = flushwrap.bp5_command(self._output(), [self.clio_executable(), "settings.json"], FLUSH_SECONDS)
        with revealing(self._output()):
            self._clio_mpi(command, cwd=str(run_dir))

    def stop(self) -> None:
        """Gray-Scott runs to completion."""

    def clean(self) -> None:
        self._clio_ensure_configured(prepare=False)
        shutil.rmtree(self._output(), ignore_errors=True)
