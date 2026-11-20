"""ParaView's pvserver as a clio-jarvis service (RL40).

``start`` launches ``supervisor.py``, which runs pvserver bound to 127.0.0.1.
When JARVIS bound a service runtime, the supervisor reports it through
jarvis-cd's ServiceRuntimeReporter (starting, ready once rank 0 accepts
connections, stopping, stopped) with rank 0's node and port as the endpoint.
Like builtin.paraview's service mode, a background start (the default for a
service) holds for the service's lifetime, and ``ready`` reads that record, so
the pipeline starts the next package once pvserver listens. Otherwise
``start`` returns once the port is listening. ``stop`` sends SIGTERM; the
supervisor stops pvserver and writes ``pvserver-stop.json`` in the state
directory. A client reaches the server through an SSH tunnel to that port.

pvserver comes from Spack's builtin ``paraview`` recipe through the contract's
install query; ``jarvis ppl install`` reuses the site's MPI and Mesa and builds
the rest, and its ``spack load`` environment puts pvserver on PATH.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import secrets
import shlex
import shutil
import signal
import sys
import time
from pathlib import Path
from typing import Any

from jarvis_cd.shell import Exec, LocalExecInfo

from clio_jarvis._contract.base import ClioService

SUPERVISOR = Path(__file__).resolve().parent / "supervisor.py"
READY_FILE = "pvserver-ready.json"
STOP_FILE = "pvserver-stop.json"
PID_FILE = "pvserver-supervisor.pid"
LOG_FILE = "pvserver.log"
DESCRIPTOR_FILE = "dataset-descriptor.json"
AUTHORIZATION_FILE = "service-authorization.token"
HOST = "localhost"


class Pvserver(ClioService):
    """A ParaView server for remote rendering of clio outputs."""

    clio_program = "pvserver"
    clio_probe_arguments = ("--version",)
    clio_capabilities = ("paraview_server",)

    _clio_service_exec: Exec | None = None
    _clio_holding: bool = False

    def _configure_menu(self) -> list[dict[str, Any]]:
        return [
            {"name": "nprocs", "msg": "pvserver processes", "type": int, "default": 1},
            {
                "name": "ppn",
                "msg": "pvserver processes per node; empty means cores_per_node, else the physical cores of the job's node",
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
                "name": "dataset",
                "msg": "Absolute path of the dataset clients open through this server (e.g. xcompact3d's data.bp5), named in the service runtime; empty means the state directory",
                "type": str,
                "default": "",
            },
            {"name": "port", "msg": "TCP port on 127.0.0.1; 0 picks a free port", "type": int, "default": 0},
            {
                "name": "connect_id",
                "msg": "Connect ID a client must present; 0 means none",
                "type": int,
                "default": 0,
            },
            {
                "name": "persist",
                "msg": "Start a new pvserver on the same port when a client disconnects (pvserver serves one session)",
                "type": bool,
                "default": True,
            },
            {
                "name": "hold",
                "msg": "Keep start running until the server stops, so a hand-run 'jarvis ppl run' serves until it is signalled",
                "type": bool,
                "default": False,
            },
            {
                "name": "max_lifetime",
                "msg": "Seconds before the server stops itself; absent means it runs until stopped",
                "type": int,
                "default": None,
                "required": False,
            },
            {"name": "start_timeout", "msg": "Seconds to wait for the port to open", "type": int, "default": 120},
            {
                "name": "state_dir",
                "msg": "Directory for the ready and stop records and the log; empty means {shared_dir}/pvserver",
                "type": str,
                "default": "",
            },
            {
                "name": "walltime",
                "msg": "Wall-time limit in seconds; absent means no limit",
                "type": int,
                "default": None,
                "required": False,
            },
            {"name": "queue", "msg": "Batch queue; empty means the site default", "type": str, "default": ""},
        ]

    def _clio_prepare(self, config: dict[str, Any]) -> None:
        Path(config["state_dir"]).mkdir(parents=True, exist_ok=True)

    # -- files ---------------------------------------------------------------

    def _clio_hosts(self) -> list[str]:
        """Hosts for the pvserver ranks: the package's hostfile (after host_slice), or none for this node."""
        hostfile = self.hostfile
        if hostfile is None or not len(hostfile) or hostfile.is_local():
            return []
        return list(hostfile.hosts)

    def _state(self, name: str) -> Path:
        self._clio_ensure_configured(prepare=False)
        return Path(self.config["state_dir"]) / name

    def _read_json(self, name: str) -> dict[str, Any] | None:
        try:
            return json.loads(self._state(name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def _supervisor_pid(self) -> int | None:
        try:
            return int(self._state(PID_FILE).read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            return None

    def _log_tail(self, lines: int = 20) -> str:
        try:
            return "\n".join(self._state(LOG_FILE).read_text(encoding="utf-8").splitlines()[-lines:])
        except OSError:
            return ""

    # -- lifecycle -------------------------------------------------------------

    def _runtime_path(self) -> str:
        return str(self.mod_env.get("JARVIS_SERVICE_RUNTIME_PATH") or self.env.get("JARVIS_SERVICE_RUNTIME_PATH") or "")

    def _runtime_arguments(self, state_dir: Path) -> list[str]:
        """Supervisor arguments for the service runtime JARVIS bound; none without one."""
        if not (self._runtime_path() and self.mod_env.get("JARVIS_EXECUTION_ID")):
            return []
        from jarvis_cd.service_runtime import (
            DatasetDescriptor,
            DatasetMember,
            ServiceProtocol,
            ServiceRuntimeReporter,
            calculate_dataset_fingerprint,
        )

        if not hasattr(ServiceProtocol, "TCP"):
            raise RuntimeError(
                "pvserver reports its service runtime with protocol tcp, which needs "
                "jarvis-cd 4007fd14 or newer (ServiceProtocol.TCP); update jarvis-cd"
            )

        dataset = str(self.config.get("dataset") or "").strip()
        if dataset and not posixpath.isabs(dataset):
            raise ValueError(f"pvserver dataset must be an absolute path on the site, not {dataset!r}")
        location = posixpath.normpath(dataset or Path(state_dir).resolve().as_posix())
        suffix = posixpath.splitext(location)[1].lower()
        kind = "live-dataset" if dataset else "paraview-server"
        format_name = {".bp5": "adios2-bp5", ".bp": "adios2-bp"}.get(suffix, suffix.lstrip(".") or "paraview-client-server")
        dataset_id = re.sub(r"[^A-Za-z0-9._:-]", "-", f"{self.pkg_id}.dataset").lstrip("._:-")[:256] or "pvserver.dataset"
        members = (DatasetMember(index=0, location=location),)
        descriptor = DatasetDescriptor(
            dataset_id=dataset_id,
            kind=kind,
            format=format_name,
            members=members,
            fingerprint=calculate_dataset_fingerprint(
                dataset_id=dataset_id, kind=kind, format=format_name, members=members
            ),
        )
        descriptor_path = state_dir / DESCRIPTOR_FILE
        descriptor_path.write_text(descriptor.to_json() + "\n", encoding="utf-8")
        token_path = state_dir / AUTHORIZATION_FILE
        token_path.unlink(missing_ok=True)
        handle = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(handle, "w", encoding="ascii") as stream:
            stream.write(secrets.token_hex(32) + "\n")
        return [
            "--descriptor", str(descriptor_path),
            "--service-instance-id", ServiceRuntimeReporter.new_service_instance_id(),
            "--authorization-file", str(token_path),
        ]

    def start(self) -> None:
        self._clio_ensure_configured(prepare=True)
        config = self.config
        state_dir = Path(config["state_dir"])
        state_dir.mkdir(parents=True, exist_ok=True)
        for name in (READY_FILE, STOP_FILE):
            self._state(name).unlink(missing_ok=True)
        argv = [
            sys.executable,
            str(SUPERVISOR),
            "--state-dir", str(state_dir),
            "--executable", self.clio_executable(),
            "--port", str(int(config["port"])),
            "--nprocs", str(int(config["nprocs"])),
            "--ppn", str(self.clio_ppn() or 0),
            "--hosts", ",".join(self._clio_hosts()),
            "--connect-id", str(int(config["connect_id"])),
            "--start-timeout", str(int(config["start_timeout"])),
            "--grace", str(self._grace()),
        ]
        argv += self._runtime_arguments(state_dir)
        if config.get("max_lifetime") not in (None, ""):
            argv += ["--max-lifetime", str(int(config["max_lifetime"]))]
        if config.get("persist"):
            argv.append("--persist")
        self._clio_service_exec = Exec(
            shlex.join(argv),
            LocalExecInfo(
                env=self.mod_env,
                cwd=str(state_dir),
                exec_async=True,
                hide_output=False,
                line_callback=self.runtime_line_callback(),
            ),
        )
        self._clio_service_exec.run()

        deadline = time.monotonic() + int(config["start_timeout"]) + 15
        while True:
            if self._read_json(READY_FILE) is not None:
                background = getattr(self, "starts_in_background", None)
                if config.get("hold") or (background is not None and background()):
                    self._clio_holding = True
                    try:
                        self._hold()
                        code = self._finish()
                    finally:
                        self._clio_holding = False
                    if code not in (0, None):
                        raise RuntimeError(f"pvserver supervisor exited with status {code}; log tail:\n{self._log_tail()}")
                return
            process = self._clio_service_exec.processes.get(HOST)
            if process is None or process.poll() is not None or time.monotonic() > deadline:
                break
            time.sleep(0.2)
        self._terminate(signal.SIGTERM)
        self._finish()
        raise RuntimeError(f"pvserver did not start; log tail:\n{self._log_tail()}")

    def ready(self) -> bool | None:
        """The service runtime's answer when JARVIS bound one, else the state files.

        True once the runtime says ready (or degraded), False once it says
        stopped or failed, None while starting. Without a runtime the stop
        record means False and the ready record True.
        """
        if self._runtime_path():
            return super().ready()
        if self._read_json(STOP_FILE) is not None:
            return False
        if self._read_json(READY_FILE) is not None:
            return True
        return None

    def _hold(self) -> None:
        """Serve until the supervisor ends; a signal to this process stops the server.

        A background start (``Pipeline.start`` runs a service's start in a
        thread) holds here like builtin.paraview's service mode, and so does
        ``hold`` for a hand-run ``jarvis ppl run``. In the main thread SIGTERM,
        SIGINT or SIGHUP to JARVIS is passed to the supervisor, which stops
        pvserver and writes the stop record; ``stop`` sends the same SIGTERM
        from another thread and waits for the supervisor to finish.
        """
        service = self._clio_service_exec
        process = service.processes.get(HOST) if service is not None else None
        if process is None:
            return

        def forward(number, _frame):
            self._terminate(signal.SIGTERM)

        previous = {}
        for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            try:
                previous[number] = signal.signal(number, forward)
            except ValueError:  # not the main thread: the caller stops the service itself
                break
        try:
            while process.poll() is None:
                time.sleep(0.5)
        finally:
            for number, handler in previous.items():
                signal.signal(number, handler)

    def _grace(self) -> int:
        return int(self.clio_contract().data["service"]["stop"].get("grace_seconds", 15))

    def _terminate(self, number: int) -> None:
        pid = self._supervisor_pid()
        if pid is None:
            return
        try:
            os.kill(pid, number)
        except ProcessLookupError:
            pass

    def _finish(self) -> int | None:
        """Wait for the supervisor this instance started; this finalizes its progress."""
        service = self._clio_service_exec
        if service is None:
            return None
        process = service.processes.get(HOST)
        deadline = time.monotonic() + self._grace() + 10
        while process is not None and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.2)
        if process is not None and process.poll() is None:
            service.kill(HOST)
        code = service.wait(HOST)
        self._clio_service_exec = None
        return code

    def stop(self) -> None:
        """SIGTERM the supervisor and wait for it; nothing running is not an error."""
        self._terminate(signal.SIGTERM)
        if self._clio_service_exec is not None and not self._clio_holding:
            code = self._finish()
            if code not in (0, None):
                raise RuntimeError(f"pvserver supervisor exited with status {code}")
            return
        # The holding start (or another process) waits for the supervisor; wait
        # for its stop record, within jarvis-cd's stop timeout.
        deadline = time.monotonic() + self._grace() + 10
        while self._supervisor_pid() is not None and time.monotonic() < deadline:
            time.sleep(0.2)

    def kill(self) -> None:
        self._terminate(signal.SIGKILL)
        ready = self._read_json(READY_FILE) or {}
        if ready.get("server_pid"):
            try:
                os.killpg(int(ready["server_pid"]), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        self._state(PID_FILE).unlink(missing_ok=True)

    def status(self) -> str:
        pid = self._supervisor_pid()
        if pid is None:
            return "stopped"
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return "stopped"
        ready = self._read_json(READY_FILE)
        return f"running on port {ready['port']}" if ready else "starting"

    def clean(self) -> None:
        if self._supervisor_pid() is None:
            shutil.rmtree(self.config["state_dir"], ignore_errors=True)
