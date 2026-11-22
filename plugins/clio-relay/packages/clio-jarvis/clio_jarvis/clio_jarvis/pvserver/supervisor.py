#!/usr/bin/env python3
"""Run one pvserver for clio-jarvis and report its life in the state directory.

The supervisor picks the port (0 asks for a free one) and starts pvserver bound
to 127.0.0.1. It waits until the port is listening, then prints
``clio-pvserver ready port=N`` and writes ``pvserver-ready.json``. It never
connects to check the port, because pvserver serves the first client that
connects.

pvserver serves one client session and exits when that client disconnects
(this package does not use ``--multi-clients``). With ``--persist`` the
supervisor then starts a new pvserver on the same port and prints
``clio-pvserver restarted port=N``, so the service outlives its clients.

On SIGTERM or SIGINT, at the lifetime limit, or when pvserver exits without
being restarted, it stops the server and writes ``pvserver-stop.json``
(clio.service-stop.v1).

A server that never listens fails typed: the stop record's ``cause`` names why
(start_timeout, exited_before_ready, stopped_before_ready, or a known launcher
failure such as mpi_wireup_failed) with the last output lines, the hosts and
the launch's network selection, and the service runtime says failed. A known
launcher failure stops the server FAIL_FAST_SECONDS after it shows rather
than at the start timeout, so a hung launch does not hold the allocation.

When JARVIS bound a service runtime (``--descriptor`` is given), it also
reports the service through jarvis-cd's ServiceRuntimeReporter: starting once
pvserver is launched, ready once rank 0 listens, degraded and ready again
around a persist restart, stopping before it stops the server, and stopped or
failed at the end. The reported endpoint is this node (rank 0's) and the port.
jarvis-cd's ``Pkg.ready`` reads that record, and the next package in the
pipeline starts only once it says ready.

With more than one rank it runs the MPI launch JARVIS built (``--launch``): the
package asks jarvis-cd's MPI executor for the command, the same path an MPI
application launches through, so the launcher, hosts, network selection and
rank environment are JARVIS's. The supervisor only puts the chosen port in
place of PORT_PLACEHOLDER and runs it. The package orders the hosts with this
node first, so rank 0 listens where the supervisor checks.

Without a service runtime only the standard library is used, so any Python
3.9+ can run it; with one, jarvis_cd is imported (the supervisor runs under
JARVIS's Python).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

READY_FILE = "pvserver-ready.json"
STOP_FILE = "pvserver-stop.json"
PID_FILE = "pvserver-supervisor.pid"
LOG_FILE = "pvserver.log"
READY_SCHEMA = "clio.service-ready.v1"
STOP_SCHEMA = "clio.service-stop.v1"
BIND = "127.0.0.1"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, document: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((BIND, 0))
        return sock.getsockname()[1]


def listening(port: int) -> bool | None:
    """True when a socket listens on ``port``. None when /proc/net/tcp is not there."""
    seen_table = False
    for table in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(table, encoding="ascii") as handle:
                lines = handle.read().splitlines()[1:]
        except OSError:
            continue
        seen_table = True
        for line in lines:
            parts = line.split()
            if len(parts) > 3 and parts[3] == "0A" and int(parts[1].rsplit(":", 1)[1], 16) == port:
                return True
    return False if seen_table else None


#: Stands for the port in a launch built before the supervisor picks it.
PORT_PLACEHOLDER = "@CLIO_PVSERVER_PORT@"

#: Launcher output that means the ranks cannot start, by cause. Matched case-insensitively.
START_FAILURES = (
    ("mpi_wireup_failed", "cannot find a corresponding process entry"),
    ("mpi_wireup_failed", "unable to reliably start one or more daemons"),
    ("mpi_wireup_failed", "has lost communication with"),
    ("mpi_wireup_failed", "pmix_init failed"),
    ("mpi_wireup_failed", "received unexpected process identifier"),
    ("mpi_network_unreachable", "no route to host"),
    ("mpi_network_unreachable", "connection refused"),
    ("mpi_init_failed", "mpi_init has failed"),
    ("mpi_init_failed", "mpi_init_thread has failed"),
    ("mpi_init_failed", "it looks like mpi_init failed"),
    ("library_missing", "error while loading shared libraries"),
    ("pvserver_failed", "failed to bind"),
)

#: Seconds rank 0 still gets to listen after a start failure shows in the output.
FAIL_FAST_SECONDS = 60

#: What a stop record says each cause means.
CAUSE_MESSAGES = {
    "start_timeout": "rank 0 did not listen within the start timeout",
    "exited_before_ready": "pvserver exited before rank 0 listened",
    "stopped_before_ready": "the server was stopped before rank 0 listened",
    "mpi_wireup_failed": "the MPI ranks could not connect to each other",
    "mpi_network_unreachable": "a node could not reach another over the network MPI used",
    "mpi_init_failed": "MPI initialisation failed",
    "library_missing": "a shared library was not found on a node",
    "pvserver_failed": "pvserver could not bind its port",
    "report_failed": "the service runtime record could not be written",
}


def start_failure(line: str) -> str | None:
    """The cause a launcher or pvserver line names, if it is a known start failure."""
    lowered = line.lower()
    for cause, pattern in START_FAILURES:
        if pattern in lowered:
            return cause
    return None


# -- network fallback warnings ------------------------------------------------------------
# A copy of clio_jarvis/_contract/transport.py, since this script runs with only the
# standard library; tests/test_contract.py checks the two stay the same.
# UCX and libfabric warn when they skip a device they cannot use (say mlx5_0:1) and go on
# over another transport. Those lines stay out of the failure evidence and the stop record
# reports them under "transport" as information, never as the cause.

UCX_WARN = re.compile(r"\bUCX\s+WARN\b")
LIBFABRIC_WARN = re.compile(r"\blibfabric:[^\s]*<warn>")
OPENFABRICS_SKIP = re.compile(
    r"(no OpenFabrics connection schemes reported|openib BTL \(OpenFabrics support\) will be disabled|"
    r"OpenFabrics device found, but there are no active ports)",
    re.IGNORECASE,
)
UNAVAILABLE = re.compile(r"(?:device|transport|interface)\s+'([^']+)'\s+(?:is\s+)?not available", re.IGNORECASE)
BARE_UNAVAILABLE = re.compile(r"\b([A-Za-z][\w.-]*:\d+)\s+(?:is\s+)?not available", re.IGNORECASE)
OFFERED = re.compile(r"'([^']+)'\(([^)]+)\)")
TRANSPORT_SETTINGS = (
    "UCX_TLS",
    "UCX_NET_DEVICES",
    "FI_PROVIDER",
    "OMPI_MCA_pml",
    "OMPI_MCA_btl",
    "OMPI_MCA_mtl",
    "I_MPI_FABRICS",
    "I_MPI_OFI_PROVIDER",
    "MPICH_OFI_PROVIDER",
)
TRANSPORT_NOTE = (
    "Informational: the network library could not use a device it probed and fell back to "
    "another transport, and the ranks went on communicating. These lines are not the cause "
    "of the run's result and do not call for a change to the site's network settings."
)
TRANSPORT_NOTE_EARLY = (
    "Informational: the network library could not use a device it probed and offered another "
    "transport. A warning like this is printed by runs that succeed too, so it does not explain "
    "why this launch stopped; the failure is in the other lines. Do not change the site's "
    "network settings on the strength of these lines alone."
)


def transport_library(line: str) -> str | None:
    """``ucx``, ``libfabric`` or ``openfabrics`` when ``line`` is a transport fallback warning."""
    if UCX_WARN.search(line):
        return "ucx"
    if LIBFABRIC_WARN.search(line):
        return "libfabric"
    if OPENFABRICS_SKIP.search(line):
        return "openfabrics"
    return None


class TransportNotes:
    """Collects fallback warnings from the launch's output; thread safe."""

    def __init__(self, keep: int = 5) -> None:
        self.keep = keep
        self.lock = threading.Lock()
        self.libraries: list[str] = []
        self.unavailable: list[str] = []
        self.offered: dict[str, list[str]] = {}
        self.lines: list[str] = []
        self.count = 0

    def observe(self, line: str) -> bool:
        """Record ``line`` when it is a fallback warning; True if it was one."""
        which = transport_library(line)
        if which is None:
            return False
        with self.lock:
            self.count += 1
            if which not in self.libraries:
                self.libraries.append(which)
            for pattern in (UNAVAILABLE, BARE_UNAVAILABLE):
                for name in pattern.findall(line):
                    if name not in self.unavailable:
                        self.unavailable.append(name)
            if "use one or more of" in line:
                for device, kind in OFFERED.findall(line.split("use one or more of", 1)[1]):
                    devices = self.offered.setdefault(kind, [])
                    if device not in devices and len(devices) < self.keep:
                        devices.append(device)
            if len(self.lines) < self.keep and line not in self.lines:
                self.lines.append(line)
        return True

    def report(self, env=None, *, progressed: bool = True) -> dict | None:
        """The stop record's ``transport`` block, or None when no fallback was seen."""
        with self.lock:
            if not self.count:
                return None
            kinds = list(self.offered)
            if len(kinds) == 1:
                used = f"{kinds[0]} (the only transport the library offered instead)"
            elif kinds:
                used = f"one of {', '.join(kinds)} (the library offered these instead)"
            else:
                used = "a transport other than the ones named unavailable; the library does not say which at its default log level"
            settings = {name: str(env[name]) for name in TRANSPORT_SETTINGS if env and env.get(name) not in (None, "")}
            return {
                "fallback": True,
                "libraries": list(self.libraries),
                "unavailable": list(self.unavailable),
                "offered": {kind: list(devices) for kind, devices in self.offered.items()},
                "used": used,
                "launch_settings": settings,
                "warning_lines": self.count,
                "examples": list(self.lines),
                "note": TRANSPORT_NOTE if progressed else TRANSPORT_NOTE_EARLY,
            }


def transport_summary(transport: dict) -> str:
    """One line for a network fallback, worded as information."""
    skipped = ", ".join(transport.get("unavailable") or []) or "a device"
    libraries = "/".join(transport.get("libraries") or [])
    return f"info, not the cause: {libraries} skipped {skipped} and used {transport['used']}"


def pvserver_arguments(executable: str, port: int | str, connect_id: int = 0) -> list[str]:
    """One pvserver rank's command line."""
    command = [
        executable,
        "--force-offscreen-rendering",
        f"--bind-address={BIND}",
        f"--server-port={port}",
    ]
    if connect_id:
        command.append(f"--connect-id={connect_id}")
    return command


def ordered_hosts(hosts: list[str]) -> list[str]:
    """``hosts`` with this node first, so rank 0 listens where the supervisor checks."""
    names = {socket.gethostname(), socket.gethostname().split(".")[0], socket.getfqdn(), "localhost"}
    for index, host in enumerate(hosts):
        if host in names or host.split(".")[0] in names:
            return [host] + hosts[:index] + hosts[index + 1:]
    raise ValueError(f"this node ({socket.gethostname()}) is not among the hosts {hosts}")


def load_launch(path: str) -> dict:
    """The MPI launch JARVIS built: a shell command holding PORT_PLACEHOLDER and the launcher's environment."""
    launch = json.loads(Path(path).read_text(encoding="utf-8"))
    if PORT_PLACEHOLDER not in str(launch.get("command", "")):
        raise ValueError(f"the launch in {path} has no {PORT_PLACEHOLDER} for the port")
    return launch


def server_command(args: argparse.Namespace, port: int) -> tuple[list[str] | str, dict[str, str] | None]:
    """The command to start (a shell line for an MPI launch) and its environment, None meaning ours."""
    if args.launch_spec is None:
        return pvserver_arguments(args.executable, port, args.connect_id), None
    command = str(args.launch_spec["command"]).replace(PORT_PLACEHOLDER, str(port))
    environment = dict(os.environ)
    environment.update({key: str(value) for key, value in (args.launch_spec.get("env") or {}).items()})
    return command, environment


class RuntimeReport:
    """The jarvis-cd service runtime of this server; a no-op without ``--descriptor``.

    The endpoint host is this node, which runs rank 0, and the port is the one
    rank 0 listens on. The protocol is tcp (jarvis-cd 4007fd14 or newer), so
    the record's base_url is tcp://host:port and clients open cs://host:port;
    its endpoint path fields are jarvis-cd's defaults and name no route.
    """

    def __init__(self, args: argparse.Namespace, port: int, log) -> None:
        self.reporter = None
        self.lifecycle: str | None = None
        self.log = log
        if not args.descriptor:
            return
        from jarvis_cd.service_runtime import (
            DatasetDescriptor,
            ServiceProtocol,
            ServiceRuntimeAuthority,
            ServiceRuntimeReporter,
        )

        descriptor = DatasetDescriptor.from_json(Path(args.descriptor).read_text(encoding="utf-8"))
        token = Path(args.authorization_file).read_text(encoding="ascii").strip()
        self.reporter = ServiceRuntimeReporter.from_environment(
            service_instance_id=args.service_instance_id,
            host=socket.gethostname(),
            port=port,
            dataset_descriptor=descriptor,
            authority=ServiceRuntimeAuthority(scheme="bearer", token=token),
            protocol=ServiceProtocol.TCP,
        )

    def __call__(self, lifecycle: str, message: str) -> bool:
        """Append ``lifecycle``; False when the record could not be written."""
        if self.reporter is None or self.lifecycle in ("stopped", "failed"):
            return True
        from jarvis_cd.service_runtime import ServiceLifecycle

        try:
            self.reporter.report(ServiceLifecycle(lifecycle), message=message)
        except Exception as error:  # the server is still stopped and the stop record written
            self.log.write(f"# {now()} service runtime report {lifecycle} failed: {error}\n")
            self.log.flush()
            return False
        self.lifecycle = lifecycle
        return True


class Supervisor:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.state_dir = Path(args.state_dir)
        self.stop_reason: str | None = None
        self.stop_signal: str | None = None
        self.stdout_open = True
        self.accepting = threading.Event()
        self.client_seen = threading.Event()
        self.wake = threading.Event()
        self.recent: deque[str] = deque(maxlen=40)
        self.failure: tuple[str, str, float] | None = None
        self.cause: dict | None = None
        self.transport = TransportNotes()
        self.launch_env: dict | None = None

    def say(self, text: str) -> None:
        if not self.stdout_open:
            return
        try:
            sys.stdout.write(text + "\n")
            sys.stdout.flush()
        except (BrokenPipeError, OSError):
            # The launcher went away; keep serving and keep logging to the file.
            self.stdout_open = False

    def on_signal(self, number: int, _frame) -> None:
        if self.stop_reason is None:
            self.stop_reason = "signal"
            self.stop_signal = signal.Signals(number).name
        self.wake.set()

    def forward(self, pipe, log) -> None:
        for line in iter(pipe.readline, ""):
            log.write(line)
            log.flush()
            text = line.rstrip("\n")
            if self.transport.observe(text.strip()):
                # A fallback the library recovered from: logged and shown, never failure evidence.
                self.say(text)
                continue
            if text.strip():
                self.recent.append(text)
            if "Accepting connection" in line:
                self.accepting.set()
            if "Client connected" in line:
                self.client_seen.set()
            if self.failure is None and not self.accepting.is_set():
                cause = start_failure(text)
                if cause is not None:
                    self.failure = (cause, text.strip(), time.monotonic())
                    self.wake.set()
            self.say(text)
        pipe.close()

    def launch(self, port: int, log) -> tuple[subprocess.Popen, threading.Thread]:
        command, environment = server_command(self.args, port)
        self.launch_env = environment
        log.write(f"# {now()} {command if isinstance(command, str) else ' '.join(command)}\n")
        log.flush()
        self.accepting.clear()
        self.client_seen.clear()
        server = subprocess.Popen(
            command,
            shell=isinstance(command, str),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        reader = threading.Thread(target=self.forward, args=(server.stdout, log), daemon=True)
        reader.start()
        return server, reader

    def wait_listening(self, server: subprocess.Popen, port: int) -> str | None:
        """None once rank 0 listens, else why it did not: a signal, an exit, a known failure or the timeout."""
        deadline = time.monotonic() + self.args.start_timeout
        while True:
            state = listening(port)
            if state or (state is None and self.accepting.is_set()):
                return None
            if self.stop_reason is not None:
                return "stopped_before_ready"
            if server.poll() is not None:
                return self.failure[0] if self.failure else "exited_before_ready"
            if self.failure is not None and time.monotonic() > self.failure[2] + FAIL_FAST_SECONDS:
                return self.failure[0]
            if time.monotonic() >= deadline:
                return "start_timeout"
            self.wake.wait(0.2)
            self.wake.clear()

    def diagnosis(self, cause: str) -> dict:
        """The typed start failure for the stop record and the service runtime."""
        launch = self.args.launch_spec or {}
        network = launch.get("network")
        applied = (network or {}).get("applied") if isinstance(network, dict) else None
        record = {
            "code": cause,
            "message": CAUSE_MESSAGES.get(cause, cause),
            "start_timeout": self.args.start_timeout,
            "nprocs": self.args.nprocs,
            "hosts": launch.get("hosts") or [socket.gethostname()],
            "launch_network": applied or None,
            "evidence": list(self.recent)[-12:],
        }
        advisories = launch.get("advisories") or []
        if advisories:
            record["advisories"] = advisories
            record["reason_codes"] = sorted(
                {code for item in advisories if isinstance(item, dict) for code in item.get("reason_codes") or []}
            )
        if self.failure is not None:
            record["seen"] = {"cause": self.failure[0], "line": self.failure[1]}
        transport = self.transport.report(self.launch_env if self.launch_env is not None else os.environ, progressed=False)
        if transport:
            record["transport"] = transport
        if self.args.nprocs > 1 and not isinstance(network, dict):
            record["note"] = (
                "the multi-node launch had no network facts for the site; collect them before a multi-node launch"
            )
        elif isinstance(network, dict) and network.get("error"):
            record["note"] = f"the launch's network selection was not applied: {network['error']}"
        return record

    def run(self) -> int:
        args = self.args
        self.state_dir.mkdir(parents=True, exist_ok=True)
        for name in (READY_FILE, STOP_FILE):
            (self.state_dir / name).unlink(missing_ok=True)
        (self.state_dir / PID_FILE).write_text(f"{os.getpid()}\n", encoding="ascii")
        for number in (signal.SIGTERM, signal.SIGINT):
            signal.signal(number, self.on_signal)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        signal.signal(signal.SIGPIPE, signal.SIG_IGN)

        port = args.port or free_port()
        started = now()
        log = open(self.state_dir / LOG_FILE, "a", encoding="utf-8")
        host = socket.gethostname()
        try:
            runtime = RuntimeReport(args, port, log)
        except Exception as error:
            log.write(f"# {now()} service runtime unavailable: {error}\n")
            self.say(f"clio-pvserver service runtime unavailable: {error}")
            self.stop_reason = "report-failed"
            return self.finish(log, port, started, None, 0, None)
        server, reader = self.launch(port, log)
        if not runtime("starting", f"pvserver launched on {host}; waiting for rank 0 to listen on port {port}"):
            self.stop_reason = "report-failed"

        ready_at = None
        restarts = 0
        if self.stop_reason is None:
            why = self.wait_listening(server, port)
            if why is None:
                ready_at = now()
            elif why == "stopped_before_ready":
                self.cause = self.diagnosis(why)
            else:
                self.stop_reason = "failed-to-start"
                self.cause = self.diagnosis(why)
                self.say(f"clio-pvserver failed to start cause={why}: {self.cause['message']}")

        endpoint = f"cs://{host}:{port}"
        if ready_at is not None:
            ready = {
                "schema": READY_SCHEMA,
                "host": host,
                "bind": BIND,
                "port": port,
                "url": f"cs://{BIND}:{port}",
                "connect_id": args.connect_id or None,
                "persist": bool(args.persist),
                "nprocs": args.nprocs,
                "supervisor_pid": os.getpid(),
                "server_pid": server.pid,
                "service_instance_id": args.service_instance_id or None,
                "started_at": started,
                "ready_at": ready_at,
                "max_lifetime": args.max_lifetime,
                "restarts": 0,
            }
            write_json(self.state_dir / READY_FILE, ready)
            listens = (
                f"pvserver rank 0 accepts connections at {endpoint} (ParaView client-server protocol, "
                f"bound to {BIND} on {host}: reach it through an SSH tunnel to {host})"
            )
            if not runtime("ready", listens):
                self.stop_reason = "report-failed"
            self.say(f"clio-pvserver ready port={port} url=cs://{BIND}:{port}")
            end = time.monotonic() + args.max_lifetime if args.max_lifetime is not None else None
            while self.stop_reason is None:
                if end is not None and time.monotonic() > end:
                    self.stop_reason = "max-lifetime"
                    break
                code = server.poll()
                if code is None:
                    self.wake.wait(0.5)
                    continue
                reader.join(timeout=5)
                # A job-wide TERM reaches pvserver and this process together:
                # give the signal a moment to land before calling it an exit.
                self.wake.wait(1.0)
                if self.stop_reason is not None:
                    break
                # A clean exit after a client session is pvserver's normal end of
                # session; anything else is a real failure.
                if not (args.persist and code == 0 and self.client_seen.is_set()):
                    self.stop_reason = "server-exited"
                    break
                restarts += 1
                runtime("degraded", f"pvserver client session ended; restarting on port {port} (restart {restarts})")
                server, reader = self.launch(port, log)
                why = self.wait_listening(server, port)
                if why is not None:
                    if why != "stopped_before_ready":
                        self.stop_reason = self.stop_reason or "failed-to-restart"
                        self.cause = self.diagnosis(why)
                    break
                ready.update(server_pid=server.pid, restarts=restarts, restarted_at=now())
                write_json(self.state_dir / READY_FILE, ready)
                if not runtime("ready", f"{listens}; restart {restarts}"):
                    self.stop_reason = "report-failed"
                    break
                self.say(f"clio-pvserver restarted port={port} restarts={restarts}")

        if self.stop_reason in ("signal", "max-lifetime") and ready_at is not None:
            runtime("stopping", f"stopping pvserver at {endpoint} ({self.stop_reason})")
        server_code = self.stop_server(server)
        reader.join(timeout=5)
        code = self.exit_code(server_code)
        if ready_at is None or self.cause is not None:
            cause = self.cause or self.diagnosis(
                "report_failed" if self.stop_reason == "report-failed" else "stopped_before_ready"
            )
            self.cause = cause
            runtime("failed", f"pvserver at {endpoint} never served: {cause['code']}: {cause['message']}")
        elif code == 0:
            runtime("stopped", f"pvserver at {endpoint} stopped ({self.stop_reason})")
        else:
            runtime("failed", f"pvserver at {endpoint} ended: {self.stop_reason}, server exit code {server_code}")
        return self.finish(log, port, started, ready_at, restarts, server_code)

    def exit_code(self, server_code: int | None) -> int:
        if self.stop_reason in ("signal", "max-lifetime"):
            return 0
        if self.stop_reason == "server-exited":
            return server_code if server_code else 0
        return 1

    def finish(self, log, port: int, started: str, ready_at: str | None, restarts: int, server_code: int | None) -> int:
        stopped = now()
        record = {
            "schema": STOP_SCHEMA,
            "reason": self.stop_reason,
            "signal": self.stop_signal,
            "host": socket.gethostname(),
            "port": port,
            "started_at": started,
            "ready_at": ready_at,
            "stopped_at": stopped,
            "restarts": restarts,
            "server_exit_code": server_code,
            "cause": self.cause,
            "transport": self.transport.report(
                self.launch_env if self.launch_env is not None else os.environ, progressed=ready_at is not None
            ),
            "log": str(self.state_dir / LOG_FILE),
        }
        write_json(self.state_dir / STOP_FILE, record)
        if record["transport"]:
            self.say(f"clio-pvserver network {transport_summary(record['transport'])}")
        log.write(f"# {stopped} stopped: {self.stop_reason}\n")
        log.close()
        (self.state_dir / PID_FILE).unlink(missing_ok=True)
        cause = f" cause={self.cause['code']}" if self.cause else ""
        self.say(f"clio-pvserver stopped reason={self.stop_reason}{cause}")
        return self.exit_code(server_code)

    def stop_server(self, server: subprocess.Popen) -> int | None:
        """TERM pvserver's process group, then KILL it after the grace.

        The server runs in its own session, so the group holds mpiexec and every
        rank on this node; mpiexec passes TERM on to the ranks it started on
        other nodes (through ssh or srun) and exits once they have.
        """
        if server.poll() is None:
            try:
                os.killpg(server.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                server.wait(timeout=self.args.grace)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(server.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                server.wait()
        return server.returncode


def _positive_int(text: str) -> int:
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive number of seconds, not {value}")
    return value


def parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--executable", default="pvserver")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--nprocs", type=int, default=1)
    parser.add_argument(
        "--launch",
        default="",
        help=f"JSON file with the MPI launch JARVIS built (command with {PORT_PLACEHOLDER}, env); needed above one rank",
    )
    parser.add_argument("--connect-id", type=int, default=0)
    parser.add_argument("--persist", action="store_true", help="start a new pvserver on the same port after each client session")
    parser.add_argument(
        "--max-lifetime",
        type=_positive_int,
        default=None,
        help="seconds before the server stops itself; omitted means it runs until stopped",
    )
    parser.add_argument("--start-timeout", type=int, default=120)
    parser.add_argument("--grace", type=int, default=15)
    parser.add_argument("--descriptor", default="", help="dataset descriptor JSON; given when JARVIS bound a service runtime")
    parser.add_argument("--service-instance-id", default="")
    parser.add_argument("--authorization-file", default="", help="file holding the service's bearer token")
    args = parser.parse_args(argv)
    if args.descriptor and not (args.service_instance_id and args.authorization_file):
        parser.error("--descriptor needs --service-instance-id and --authorization-file")
    if args.nprocs > 1 and not args.launch:
        parser.error("more than one rank needs --launch, the MPI launch JARVIS built")
    args.launch_spec = None
    if args.launch:
        try:
            args.launch_spec = load_launch(args.launch)
        except (OSError, ValueError) as error:
            parser.error(str(error))
    return args


if __name__ == "__main__":
    sys.exit(Supervisor(parse(sys.argv[1:])).run())
