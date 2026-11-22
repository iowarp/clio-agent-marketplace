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


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _phase_stop_seconds(root: Path) -> float | None:
    """pvserver's stop_seconds in the run record's ``services_after_steps`` phase timing."""
    for path in root.rglob("*.json"):
        if path.stat().st_size > 4 * 1024 * 1024:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "services_after_steps" not in text:
            continue
        found = []

        def walk(node):
            if isinstance(node, dict):
                phase = node.get("services_after_steps")
                if isinstance(phase, dict):
                    for entry in phase.get("packages") or []:
                        if isinstance(entry, dict) and entry.get("stop_seconds") is not None:
                            found.append(float(entry["stop_seconds"]))
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        try:
            walk(json.loads(text))
        except ValueError:
            continue
        if found:
            return max(found)
    return None


def check_coupled_linger(context: dict, pvpython: str, ending: str, linger: int) -> None:
    """pvserver viewing a step (builtin.echo) stays up ``linger`` s after it returns.

    ``ending`` "elapsed" lets the linger run out: ``jarvis ppl run`` ends
    about ``linger`` s after the step, with stop reason ``linger-ended``, and
    a client attaches meanwhile. ``ending`` "signal" sends SIGTERM to JARVIS
    during a long linger, which must stop the server at once.
    """
    from clio_jarvis._contract.selftest import REPO_DIR, jarvis_command

    check = context["check"]
    facts = context["facts"]
    tag = f"coupled linger {ending}"
    work = Path(context["work"]) / f"linger-{ending}"
    root = work / "jarvis"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    env = {**os.environ, "JARVIS_ROOT": str(root)}
    port = _free_port()
    log_path = work / "jarvis.log"
    log = open(log_path, "w", encoding="utf-8")
    try:
        for step in (
            ["init", str(root / "config"), str(root / "private"), str(root / "shared")],
            ["repo", "add", str(REPO_DIR)],
            ["ppl", "create", f"linger_{ending}"],
            ["ppl", "append", "clio_jarvis.pvserver", "pkg", "nprocs=1", "persist=true", f"port={port}", f"linger={linger}"],
            ["ppl", "append", "builtin.echo"],
        ):
            result = subprocess.run(jarvis_command() + step, env=env, cwd=work, stdout=log, stderr=subprocess.STDOUT)
            if not check(f"{tag}: jarvis {' '.join(step[:2])}", result.returncode == 0, f"rc {result.returncode}"):
                return
        began = time.monotonic()
        run = subprocess.Popen(
            jarvis_command() + ["ppl", "run"], env=env, cwd=work, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
        ready_path, ready = None, {}
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline and run.poll() is None and not ready.get("lingering"):
            ready_path = ready_path or next(iter(root.rglob("pvserver-ready.json")), None)
            ready = _read(ready_path) if ready_path else {}
            time.sleep(0.5)
        lingered_at = time.monotonic()
        if not check(
            f"{tag}: the ready record says lingering once the step returned",
            ready.get("lingering") is True and ready.get("linger_seconds") == linger and bool(ready.get("linger_until")),
            {k: ready.get(k) for k in ("linger", "lingering", "linger_seconds", "linger_until", "linger_capped_by")},
        ):
            os.killpg(run.pid, signal.SIGKILL)
            return
        log.flush()
        check(
            f"{tag}: the step ran, then jarvis waits on pvserver",
            "Echo!" in log_path.read_text(encoding="utf-8", errors="replace") and run.poll() is None,
            f"rc {run.poll()}",
        )
        check(f"{tag}: still listening while it lingers", _listening(port), f"port {port}")
        if ending == "elapsed":
            ok, detail = _connect(work, pvpython, port, f"linger-{ending}")
            check(f"{tag}: pvpython attaches and renders during the linger", ok, detail)
        else:
            time.sleep(5)
            run.send_signal(signal.SIGTERM)
        try:
            code = run.wait(timeout=linger + 120 if ending == "elapsed" else 60)
        except subprocess.TimeoutExpired:
            os.killpg(run.pid, signal.SIGKILL)
            code = run.wait()
        total = round(time.monotonic() - began, 1)
        after = round(time.monotonic() - lingered_at, 1)
        stop = _read(ready_path.with_name("pvserver-stop.json"))
        block = stop.get("linger") or {}
        phase = _phase_stop_seconds(root)
        facts[f"linger_{ending}"] = {
            "port": port, "linger": linger, "exit_code": code, "run_seconds": total,
            "seconds_after_lingering": after, "services_after_steps_stop_seconds": phase, "stop": stop,
        }
        if ending == "elapsed":
            check(
                f"{tag}: it stops on its own once the linger ends, exit 0",
                code == 0 and stop.get("reason") == "linger-ended" and block.get("ended") == "elapsed"
                and block.get("seconds") == linger and not _listening(port),
                f"rc {code}, reason {stop.get('reason')}, linger {block}, {after} s after lingering",
            )
            check(
                f"{tag}: the run lasted the linger (services_after_steps stop_seconds)",
                after >= linger - 5 and phase is not None and phase >= linger - 5,
                f"stop_seconds {phase}, {after} s after lingering began, run {total} s",
            )
        else:
            check(
                f"{tag}: SIGTERM to jarvis ends the linger at once",
                stop.get("reason") == "signal" and block.get("ended") == "signal" and after < 45 and not _listening(port),
                f"rc {code}, reason {stop.get('reason')}, linger {block}, {after} s after lingering",
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
    check_coupled_linger(context, pvpython, "elapsed", 40)
    check_coupled_linger(context, pvpython, "signal", 600)
