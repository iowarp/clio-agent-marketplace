"""pvserver self-test: a ParaView client connects, renders remotely, and the server stops cleanly.

The generic runner already checked the ready event and the stop record of the
JARVIS run. This check starts the same supervisor again, connects pvpython
through 127.0.0.1, renders a sphere on the server, then sends SIGTERM.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

CLIENT = """
import sys
from paraview.simple import Connect, Disconnect, GetActiveViewOrCreate, Render, SaveScreenshot, Show, Sphere
port, png = int(sys.argv[1]), sys.argv[2]
connection = Connect("127.0.0.1", port)
assert connection is not None, "no connection"
view = GetActiveViewOrCreate("RenderView")
view.ViewSize = [400, 300]
Show(Sphere(ThetaResolution=32, PhiResolution=32), view)
Render(view)
SaveScreenshot(png, view)
print("PVCONNECT ok", connection.GetURI())
Disconnect()
"""


def _listening(port: int) -> bool:
    """True when something listens on ``port``, read from /proc/net/tcp (never by connecting)."""
    suffix = f":{port:04X}"
    for table in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            lines = Path(table).read_text(encoding="ascii").splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            fields = line.split()
            if len(fields) > 3 and fields[3] == "0A" and fields[1].endswith(suffix):
                return True
    return False


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _connect(work: Path, pvpython: str, port: int, tag: str) -> tuple[bool, str]:
    client = work / "pvconnect.py"
    client.write_text(CLIENT, encoding="utf-8")
    png = work / f"pvserver-sphere-{tag}.png"
    result = subprocess.run(
        [pvpython, "--force-offscreen-rendering", str(client), str(port), str(png)],
        capture_output=True, text=True, timeout=180,
    )
    (work / f"pvconnect-{tag}.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
    ok = result.returncode == 0 and "PVCONNECT ok" in result.stdout and png.is_file()
    return ok, f"rc {result.returncode}, {png}"


RUNNER = """trap '{jarvis} ppl stop; exit 0' TERM INT HUP
{jarvis} ppl start
while :; do sleep 60 & wait $!; done
"""


def check_relay_launch(context: dict, pvpython: str, mode: str) -> None:
    """Serve pvserver as relay does, with no max_lifetime or walltime.

    ``mode`` "start" is relay's service runner: ``jarvis ppl start`` returns
    once the server is ready, the runner holds, and SIGTERM to the runner
    runs ``jarvis ppl stop``. ``mode`` "run" is the opt-in for a hand-run
    ``jarvis ppl run`` with ``hold=true``: SIGTERM goes to JARVIS itself.
    Either way the server must keep serving until signalled, then stop
    cleanly with exit 0 and a stop record.
    """
    from clio_jarvis._contract.selftest import REPO_DIR, jarvis_command

    check = context["check"]
    facts = context["facts"]
    tag = f"relay {mode}"
    work = Path(context["work"]) / f"relay-{mode}"
    root = work / "jarvis"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    env = {**os.environ, "JARVIS_ROOT": str(root)}
    port = _free_port()
    args = ["nprocs=2", "ppn=2", "persist=true", f"port={port}"]
    if mode == "run":
        args.append("hold=true")
    log_path = work / "jarvis.log"
    log = open(log_path, "w", encoding="utf-8")
    try:
        for step in (
            ["init", str(root / "config"), str(root / "private"), str(root / "shared")],
            ["repo", "add", str(REPO_DIR)],
            ["ppl", "create", f"relay_{mode}"],
            ["ppl", "append", "clio_jarvis.pvserver", "pkg", *args],
        ):
            result = subprocess.run(jarvis_command() + step, env=env, cwd=work, stdout=log, stderr=subprocess.STDOUT)
            if not check(f"{tag}: jarvis {' '.join(step[:2])}", result.returncode == 0, f"rc {result.returncode}"):
                return
        if mode == "start":
            runner = work / "runner.sh"
            runner.write_text(RUNNER.format(jarvis=shlex.join(jarvis_command())), encoding="utf-8")
            command = ["bash", str(runner)]
        else:
            command = jarvis_command() + ["ppl", "run"]
        run = subprocess.Popen(command, env=env, cwd=work, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        ready_path = None
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline and run.poll() is None and ready_path is None:
            ready_path = next(iter(work.rglob("pvserver-ready.json")), None)
            time.sleep(0.5)
        if not check(f"{tag}: ready with no max_lifetime", ready_path is not None, f"port {port}, rc {run.poll()}"):
            os.killpg(run.pid, signal.SIGKILL)
            return
        ready = json.loads(ready_path.read_text(encoding="utf-8"))
        check(
            f"{tag}: records under {{shared_dir}}/pvserver, not the working directory",
            ready_path.parent.name == "pvserver"
            and (root / "shared") in ready_path.parents
            and not (work / "pvserver-ready.json").exists(),
            str(ready_path),
        )
        check(f"{tag}: ready record has no lifetime", ready.get("max_lifetime") is None, ready.get("max_lifetime"))
        record_path = next(iter(root.rglob("clio-contract.json")), None)
        check(f"{tag}: clio-contract.json written", record_path is not None, str(record_path))
        record = json.loads(record_path.read_text(encoding="utf-8")) if record_path else {"config": {}, "service": {}}
        check(
            f"{tag}: no max_lifetime or walltime in the resolved record",
            record["config"].get("max_lifetime") is None
            and record["config"].get("walltime") is None
            and "duration" not in (record.get("resources") or {})
            and record["service"].get("max_lifetime") is None,
            {"config": {k: record["config"].get(k) for k in ("max_lifetime", "walltime", "hold")}, "resources": record.get("resources")},
        )
        held = 45
        time.sleep(held)
        if mode == "start":
            log.flush()
            check(f"{tag}: jarvis ppl start returned once ready (hold off)", "[START] END" in log_path.read_text(encoding="utf-8"), None)
        check(f"{tag}: still serving after {held} s", run.poll() is None and _listening(port), f"rc {run.poll()}")
        ok, detail = _connect(work, pvpython, port, mode)
        check(f"{tag}: pvpython connects and renders", ok, detail)
        time.sleep(5)
        check(f"{tag}: still serving after the client left", run.poll() is None and _listening(port), f"rc {run.poll()}")
        began = time.monotonic()
        run.send_signal(signal.SIGTERM)  # the launcher signals its own program only
        try:
            code = run.wait(timeout=120)
        except subprocess.TimeoutExpired:
            os.killpg(run.pid, signal.SIGKILL)
            code = run.wait()
        seconds = round(time.monotonic() - began, 1)
        try:
            os.killpg(run.pid, signal.SIGTERM)  # the runner's idle sleep
        except ProcessLookupError:
            pass
        stop_path = ready_path.with_name("pvserver-stop.json")
        stop = json.loads(stop_path.read_text(encoding="utf-8")) if stop_path.is_file() else {}
        supervisor_gone = not ready_path.with_name("pvserver-supervisor.pid").exists()
        facts[f"relay_{mode}"] = {"port": port, "held_seconds": held, "stop_seconds": seconds, "exit_code": code, "stop": stop}
        what = "runs jarvis ppl stop" if mode == "start" else "to jarvis"
        check(
            f"{tag}: SIGTERM {what}, pvserver stops, exit 0",
            code == 0 and stop.get("reason") == "signal" and supervisor_gone and not _listening(port),
            f"rc {code} in {seconds} s, reason {stop.get('reason')}, restarts {stop.get('restarts')}, supervisor gone {supervisor_gone}",
        )
    finally:
        log.close()


def _wait_restart(state: Path, supervisor: subprocess.Popen, restarts: int = 1, timeout: float = 60) -> bool:
    """Wait until the ready record counts ``restarts`` restarts."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and supervisor.poll() is None:
        try:
            ready = json.loads((state / "pvserver-ready.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            ready = {}
        if int(ready.get("restarts") or 0) >= restarts:
            return True
        time.sleep(0.2)
    return False


def check(context: dict) -> None:
    check = context["check"]
    config = context["config"]
    pvpython = context["pvpython"]
    if not pvpython:
        check("pvpython connects and renders", True, "skipped: pvpython is not on PATH (spack load paraview)")
        return
    pvserver = str(Path(pvpython).with_name("pvserver"))
    work = Path(context["work"])
    state = work / "pvserver-live"
    supervisor = subprocess.Popen(
        [
            sys.executable, str(HERE / "supervisor.py"),
            "--state-dir", str(state),
            "--executable", pvserver,
            # One rank: above one the launch comes from JARVIS through the package.
            "--nprocs", "1",
            "--persist",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    ready = None
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline and supervisor.poll() is None:
        path = state / "pvserver-ready.json"
        if path.is_file():
            ready = json.loads(path.read_text(encoding="utf-8"))
            break
        time.sleep(0.2)
    if not check("supervisor reports ready", ready is not None, ready and ready.get("url")):
        supervisor.kill()
        return
    check("supervisor started with no max_lifetime reports none", ready.get("max_lifetime") is None, ready.get("max_lifetime"))
    try:
        client = work / "pvconnect.py"
        client.write_text(CLIENT, encoding="utf-8")
        for session in (1, 2):
            if session == 2:
                restarted = _wait_restart(state, supervisor)
                if not check("a new pvserver listens on the same port after the client leaves", restarted, f"port {ready['port']}"):
                    break
            png = work / f"pvserver-sphere-{session}.png"
            result = subprocess.run(
                [pvpython, "--force-offscreen-rendering", str(client), str(ready["port"]), str(png)],
                capture_output=True, text=True, timeout=180,
            )
            (work / f"pvconnect-{session}.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
            ok = result.returncode == 0 and "PVCONNECT ok" in result.stdout
            check(f"client {session}: pvpython connects and renders on the server", ok and png.is_file(), f"rc {result.returncode}, {png}")
        restarted = _wait_restart(state, supervisor, restarts=2)
        check("service still running after both clients left", restarted and supervisor.poll() is None, None)
    finally:
        supervisor.send_signal(signal.SIGTERM)
        try:
            code = supervisor.wait(timeout=60)
        except subprocess.TimeoutExpired:
            supervisor.kill()
            code = supervisor.wait()
    record_path = state / "pvserver-stop.json"
    record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.is_file() else {}
    check("SIGTERM stops it with exit 0 and a stop record", code == 0 and record.get("reason") == "signal", f"rc {code}, {record.get('reason')}")
    check_relay_launch(context, pvpython, "start")
    check_relay_launch(context, pvpython, "run")
