"""Run one package's RL40 self-test through jarvis-cd and check what it reported.

The run uses a private ``JARVIS_ROOT`` under the work directory, so it never
touches the user's JARVIS state. Steps: ``jarvis init``, ``jarvis repo add``,
``jarvis ppl load`` of a one-package pipeline with the contract's self-test
parameters, ``jarvis ppl install +check`` (the package's Spack install must
already be satisfied; the self-test never builds it), ``jarvis ppl run`` with a
known execution id. The checks then read
the execution's progress and artifact records, the package's
``clio-contract.json``, the output itself through ParaView's reader (when
``pvpython`` from ParaView's Spack install is on PATH), and the package's own
``selftest.py``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from .runtime import SERVICE_READY_SCHEMA, STEP_SCHEMA
from .spec import (
    REPO_PACKAGES_DIR,
    STOP_RECORD_SCHEMA,
    Contract,
    evaluate,
    is_view,
    load_contract,
    render,
    validate_view_descriptor,
)

REPO_DIR = REPO_PACKAGES_DIR.parent
VTXCHECK = Path(__file__).resolve().parent / "vtxcheck.py"
REPORT_SCHEMA = "clio.selftest-report.v1"


class CheckFailed(AssertionError):
    pass


@dataclass
class Report:
    package: str
    work: Path
    checks: list[dict[str, Any]] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)

    def check(self, name: str, ok: bool, detail: Any = None) -> bool:
        self.checks.append({"check": name, "ok": bool(ok), "detail": detail})
        mark = "ok  " if ok else "FAIL"
        suffix = f": {detail}" if detail not in (None, "") else ""
        print(f"[selftest {self.package}] {mark} {name}{suffix}", flush=True)
        return bool(ok)

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(item["ok"] for item in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": REPORT_SCHEMA,
            "package": self.package,
            "passed": self.passed,
            "work": str(self.work),
            "checks": self.checks,
            "facts": self.facts,
        }


def parse_overrides(items: list[str]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for item in items:
        name, sep, text = item.partition("=")
        if not sep or not name:
            raise SystemExit(f"--set needs name=value, not {item!r}")
        values[name] = yaml.safe_load(text) if text else ""
    return values


def jarvis_command() -> list[str]:
    found = shutil.which("jarvis")
    if found:
        return [found]
    return [sys.executable, "-c", "from jarvis_cd.core.cli import main; main()"]


def _last_json(text: str) -> dict[str, Any]:
    """The JSON object a ``+json`` command printed, pretty or on one line."""
    text = text.strip()
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except ValueError:
        pass
    for line in reversed(text.splitlines()):
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    start = text.find("{")
    try:
        value = json.loads(text[start:]) if start >= 0 else {}
    except ValueError:
        value = {}
    return value if isinstance(value, dict) else {}


def read_jsonl(paths: list[Path]) -> list[dict[str, Any]]:
    records = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except ValueError:
                    continue
    records.sort(key=lambda r: (r.get("sequence", 0), r.get("observed_at_epoch", 0)))
    return records


class SelfTest:
    def __init__(
        self,
        package: str,
        *,
        overrides: Mapping[str, Any] | None = None,
        work: str | Path | None = None,
    ) -> None:
        self.contract: Contract = load_contract(REPO_PACKAGES_DIR / package)
        self.package = package
        self.params = {**self.contract.data["selftest"]["params"], **dict(overrides or {})}
        stamp = time.strftime("%Y%m%d-%H%M%S")
        base = Path(work).expanduser() if work else Path.home() / ".cache" / "clio-jarvis-selftest"
        self.work = (base / f"{package}-{stamp}").resolve()
        # ParaView's Spack install, loaded in the calling shell (spack load paraview).
        self.pvpython = shutil.which("pvpython") or ""
        self.jarvis_root = self.work / "jarvis"
        self.pipeline = f"clio-selftest-{package}"
        self.execution_id = f"selftest-{package}-{stamp}".replace("_", "-")
        self.report = Report(package, self.work)
        self.env = {**os.environ, "JARVIS_ROOT": str(self.jarvis_root)}

    # -- jarvis ----------------------------------------------------------------

    def jarvis(self, *args: str, timeout: float = 300, log: str | None = None) -> subprocess.CompletedProcess:
        command = jarvis_command() + list(args)
        print(f"[selftest {self.package}] $ {shlex.join(args)}", flush=True)
        result = subprocess.run(
            command,
            env=self.env,
            cwd=str(self.work),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if log:
            (self.work / log).write_text(
                f"$ {shlex.join(command)}\n# rc {result.returncode}\n"
                f"## stdout\n{result.stdout}\n## stderr\n{result.stderr}\n",
                encoding="utf-8",
            )
        return result

    def execution_root(self) -> Path | None:
        matches = sorted(self.jarvis_root.rglob(f"executions/{self.execution_id}"))
        return next((m for m in matches if m.is_dir()), None)

    # -- run -------------------------------------------------------------------

    def run(self) -> Report:
        self.work.mkdir(parents=True, exist_ok=True)
        report = self.report
        report.facts.update(
            {
                "package": self.contract.pkg_type,
                "version": self.contract.version,
                "sha256": self.contract.sha256,
                "params": self.params,
                "execution_id": self.execution_id,
            }
        )
        started = time.monotonic()
        try:
            self._run_pipeline()
            root = self.execution_root()
            if not report.check("execution directory exists", root is not None, str(root)):
                return self._finish(started)
            config = self._check_record(root)
            progress = read_jsonl(sorted((root / "progress").glob("*.jsonl")))
            artifacts = read_jsonl(sorted((root / "artifacts").glob("*.jsonl")))
            report.facts["progress_events"] = len(progress)
            report.facts["artifact_events"] = len(artifacts)
            if self.contract.kind == "service":
                self._check_service(progress, config)
            else:
                self._check_application(progress, artifacts, config)
            self._run_package_check(root, config, progress, artifacts)
        except CheckFailed as exc:
            report.check("self-test aborted", False, str(exc))
        except subprocess.TimeoutExpired as exc:
            report.check("self-test finished in time", False, f"timed out: {exc.cmd[-3:]}")
        return self._finish(started)

    def _finish(self, started: float) -> Report:
        report = self.report
        report.facts["seconds"] = round(time.monotonic() - started, 1)
        path = self.work / "selftest-report.json"
        path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        verdict = "PASSED" if report.passed else "FAILED"
        print(f"[selftest {self.package}] {verdict} in {report.facts['seconds']} s; report {path}", flush=True)
        return report

    def _run_pipeline(self) -> None:
        report = self.report
        root = self.jarvis_root
        result = self.jarvis("init", str(root / "config"), str(root / "private"), str(root / "shared"), log="jarvis-init.log")
        if not report.check("jarvis init", result.returncode == 0, result.stderr[-400:] if result.returncode else None):
            raise CheckFailed("jarvis init failed")
        result = self.jarvis("repo", "add", str(REPO_DIR), log="jarvis-repo-add.log")
        if not report.check("jarvis repo add", result.returncode == 0, result.stderr[-400:] if result.returncode else None):
            raise CheckFailed("jarvis repo add failed")
        pipeline = {
            "name": self.pipeline,
            "pkgs": [{"pkg_type": self.contract.pkg_type, "pkg_name": self.package, **self.params}],
        }
        pipeline_file = self.work / "pipeline.yaml"
        pipeline_file.write_text(yaml.safe_dump(pipeline, sort_keys=False), encoding="utf-8")
        result = self.jarvis("ppl", "load", "yaml", str(pipeline_file), log="jarvis-ppl-load.log")
        if not report.check("jarvis ppl load", result.returncode == 0, result.stderr[-400:] if result.returncode else None):
            raise CheckFailed("jarvis ppl load failed")
        # The software comes from the package's Spack linkage only; the self-test never builds it.
        result = self.jarvis("ppl", "install", "+check", "+json", timeout=900, log="jarvis-ppl-install-check.log")
        install = _last_json(result.stdout)
        report.facts["install"] = install.get("installers")
        if not report.check(
            "Spack install satisfied",
            result.returncode == 0 and install.get("satisfied") is True,
            None if install.get("satisfied") else (install.get("issues") or result.stderr[-400:]),
        ):
            raise CheckFailed(
                f"{self.contract.data['install']['query']!r} is not installed: run jarvis ppl install"
            )
        limit = int(self.contract.data["selftest"]["max_seconds"])
        began = time.monotonic()
        result = self.jarvis(
            "ppl", "run", "current", f"--execution_id={self.execution_id}", "+json",
            timeout=limit + 120, log="jarvis-ppl-run.log",
        )
        seconds = round(time.monotonic() - began, 1)
        report.facts["run_seconds"] = seconds
        report.check("jarvis ppl run exits 0", result.returncode == 0, f"rc {result.returncode}, {seconds} s")
        report.check(f"run within {limit} s", seconds <= limit, f"{seconds} s")
        state = self.jarvis("execution", "get", self.execution_id, f"--pipeline_id={self.pipeline}", "+json")
        record = _last_json(state.stdout)
        report.facts["execution_state"] = record.get("state")
        report.check("execution completed", record.get("state") == "completed", record.get("state"))

    # -- checks ------------------------------------------------------------------

    def _check_record(self, root: Path) -> dict[str, Any]:
        report = self.report
        records = sorted(root.rglob("clio-contract.json"))
        if not report.check("clio-contract.json written", bool(records), [str(p) for p in records]):
            raise CheckFailed("no clio-contract.json")
        document = json.loads(records[0].read_text(encoding="utf-8"))
        report.check("record schema", document.get("schema") == "clio.package-resolved.v1", document.get("schema"))
        report.check(
            "record pins the package sha256",
            document.get("sha256") == self.contract.sha256,
            document.get("sha256"),
        )
        inputs = document.get("inputs") or []
        missing = [item["path"] for item in inputs if not item.get("sha256")]
        report.check("every provenance input has a digest", not missing, missing or f"{len(inputs)} inputs")
        report.facts["resources"] = document.get("resources")
        return dict(document.get("config") or {})

    def _check_application(
        self, progress: list[dict[str, Any]], artifacts: list[dict[str, Any]], config: Mapping[str, Any]
    ) -> None:
        report = self.report
        spec = self.contract.data["progress"]
        expected = evaluate(spec.get("total"), config)
        report.facts["expected_steps"] = expected
        steps = [
            event
            for event in progress
            if (event.get("metadata") or {}).get("clio", {}).get("schema") == STEP_SCHEMA
            and event.get("state") == "running"
        ]
        numbers = [event["metadata"]["clio"]["step"] for event in steps]
        report.facts["step_records"] = len(numbers)
        report.check(
            "one progress record per output step, 1..N",
            numbers == list(range(1, int(expected or 0) + 1)),
            f"{len(numbers)} records, expected {expected}; first {numbers[:3]} last {numbers[-3:]}",
        )
        bad = []
        for event in steps:
            clio = event["metadata"]["clio"]
            try:
                validate_view_descriptor(clio["view"])
            except ValueError as exc:
                bad.append(f"step {clio['step']}: {exc}")
                continue
            if not clio["view"].get("growing") or clio.get("expected_steps") != expected:
                bad.append(f"step {clio['step']}: growing or expected_steps wrong")
        report.check("every step record carries a valid growing view descriptor", not bad, bad[:3] or None)
        if steps:
            first = steps[0]["metadata"]["clio"]
            visible = first["visible_steps"]
            wanted = 0 if spec.get("announces") == "before-write" else 1
            report.check("visible_steps follows announces", visible == wanted, f"step 1 shows {visible}")
            report.facts["view_descriptor"] = first["view"]
            stamps = [float(event.get("observed_at_epoch") or 0) for event in steps]
            gaps = sorted(b - a for a, b in zip(stamps, stamps[1:]))
            if gaps:
                report.facts["seconds_per_step_median"] = round(gaps[len(gaps) // 2], 2)
        last = progress[-1] if progress else {}
        clio = (last.get("metadata") or {}).get("clio") or {}
        view = clio.get("view") or {}
        report.check(
            "last progress record is completed with a closed view",
            last.get("state") == "completed" and view.get("growing") is False,
            f"{last.get('state')}, growing {view.get('growing')}",
        )

        final: dict[str, dict[str, Any]] = {}
        for event in artifacts:
            final[event.get("logical_name", "")] = event
        for output in self.contract.data["outputs"]:
            if not is_view(output):
                # Statistics and restart are written only when the run asks for them.
                continue
            event = final.get(output["name"])
            path = render(output["path"], config)
            report.check(
                f"artifact {output['name']} finalized",
                event is not None and event.get("state") == "finalized",
                event.get("state") if event else "no artifact event",
            )
            exists = Path(path).exists()
            report.check(f"output {output['name']} exists", exists, path)
            if exists:
                self._check_with_reader(output, path, int(expected or 0))

    def _check_with_reader(self, output: Mapping[str, Any], path: str, expected: int) -> None:
        report = self.report
        if output.get("reader") != "ADIOS2VTXReader":
            return
        if not self.pvpython:
            report.check("ParaView reader check", True, "skipped: no pvpython on PATH (spack load paraview)")
            return
        arrays = list(output.get("arrays") or [])
        array = (output.get("display") or {}).get("array") or (arrays[0] if arrays else "")
        png = self.work / f"{output['name']}-last.png"
        command = [self.pvpython, "--force-offscreen-rendering", str(VTXCHECK), path, array, str(png)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        (self.work / f"vtxcheck-{output['name']}.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
        line = next((l for l in result.stdout.splitlines() if l.startswith("VTXCHECK {")), None)
        if not report.check("ADIOS2VTXReader opens the output", result.returncode == 0 and line is not None, f"rc {result.returncode}"):
            return
        seen = json.loads(line[len("VTXCHECK "):])
        report.facts[f"reader_{output['name']}"] = seen
        report.check("reader sees every step", seen["steps"] == expected, f"{seen['steps']} of {expected}")
        present = set(seen["point_arrays"]) | set(seen["cell_arrays"])
        missing = [name for name in arrays if name not in present]
        report.check("reader sees every array", not missing, missing or sorted(present))
        times = seen["times_head"] + seen["times_tail"]
        report.check(
            "time advances",
            len(times) >= 2 and times[-1] > times[0],
            f"head {seen['times_head']} tail {seen['times_tail']}",
        )
        first, last = seen.get("first_range"), seen.get("last_range")
        report.check("field changes over the run", first != last, f"first {first} last {last}")
        report.check("screenshot written", png.is_file(), str(png))

    def _check_service(self, progress: list[dict[str, Any]], config: Mapping[str, Any]) -> None:
        report = self.report
        ready = [
            event
            for event in progress
            if (event.get("metadata") or {}).get("clio", {}).get("schema") == SERVICE_READY_SCHEMA
        ]
        port = None
        if ready:
            ports = ready[0]["metadata"]["clio"]["service"]["ports"]
            port = ports[0].get("port") if ports else None
        report.facts["ready_port"] = port
        report.check(
            "ready event with the chosen port",
            len(ready) == 1 and ready[0].get("state") == "ready" and isinstance(port, int) and port > 0,
            f"{len(ready)} ready events, port {port}",
        )
        last = progress[-1] if progress else {}
        report.check("last progress record is completed", last.get("state") == "completed", last.get("state"))
        stop = self.contract.service(config)["stop"]
        path = Path(stop["writes"])
        if not report.check("stop record written", path.is_file(), str(path)):
            return
        record = json.loads(path.read_text(encoding="utf-8"))
        report.facts["stop_record"] = record
        report.check("stop record schema", record.get("schema") == STOP_RECORD_SCHEMA, record.get("schema"))
        report.check(
            "stopped by the contract's signal",
            record.get("reason") == "signal" and record.get("signal") == stop["signal"],
            f"{record.get('reason')} {record.get('signal')}",
        )
        report.check("stop record names the ready port", record.get("port") == port, record.get("port"))

    def _run_package_check(
        self,
        root: Path,
        config: Mapping[str, Any],
        progress: list[dict[str, Any]],
        artifacts: list[dict[str, Any]],
    ) -> None:
        script = self.contract.data["selftest"].get("script")
        if not script:
            return
        path = self.contract.pkg_dir / script
        spec = importlib.util.spec_from_file_location(f"clio_selftest_{self.package}", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        context = {
            "contract": self.contract,
            "config": dict(config),
            "execution_root": root,
            "progress": progress,
            "artifacts": artifacts,
            "pvpython": self.pvpython,
            "work": self.work,
            "check": self.report.check,
            "facts": self.report.facts,
        }
        try:
            module.check(context)
        except Exception as exc:  # the package's own check failing is a failed self-test
            self.report.check(f"{script} check", False, f"{type(exc).__name__}: {exc}")
