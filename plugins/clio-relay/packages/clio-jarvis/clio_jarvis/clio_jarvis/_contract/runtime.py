"""Progress and artifact providers for every clio-jarvis package, driven by its contract.

Each package ships two one-line shims, ``progress.py`` and ``artifacts.py``,
that jarvis-cd discovers beside ``pkg.py``. They call :func:`progress_adapter`
and :func:`artifact_adapter` here. The contract's ``progress`` part says which
stdout line marks a written step; this module turns those lines into RL40
progress records, each carrying the output's view descriptor (RL43).
"""

from __future__ import annotations

import glob
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from jarvis_cd.artifacts.provider import ArtifactObservation
from jarvis_cd.artifacts.schema import (
    ArtifactLocation,
    ArtifactOwnership,
    ArtifactRole,
    ArtifactState,
    ArtifactStructure,
    new_artifact_id,
)
from jarvis_cd.progress import LineBuffer, ProgressObservation, ProgressState

from .files import fresh_size
from .spec import VIEW_ROLE, Contract, evaluate, is_view, load_contract

STEP_SCHEMA = "clio.step.v1"
SERVICE_READY_SCHEMA = "clio.service-ready.v1"

_STRUCTURES = {
    "file": ArtifactStructure.FILE,
    "directory": ArtifactStructure.DIRECTORY,
    "glob": ArtifactStructure.COLLECTION,
}
_ROLES = {"restart": ArtifactRole.CHECKPOINT}


def _exists(path: str, kind: str) -> bool:
    if kind == "glob":
        return bool(glob.glob(path))
    return Path(path).exists()


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value <= 0 or int(value) != value:
        return None
    return int(value)


def _number(text: str) -> int | float | str:
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            continue
    return text


def _contract_for(pkg_dir: Path, package: Mapping[str, Any]) -> Contract | None:
    contract = load_contract(pkg_dir)
    if package.get("pkg_type") != contract.pkg_type:
        return None
    return contract


@dataclass
class _Event:
    kind: str  # "step", "ready" or "done"
    step: int = 0
    fields: dict[str, Any] = field(default_factory=dict)


class _LineReader:
    """Match a package's stdout against the contract's progress patterns."""

    def __init__(self, contract: Contract, config: Mapping[str, Any]) -> None:
        progress = contract.data["progress"]
        self.step_re = re.compile(progress["step_pattern"]) if "step_pattern" in progress else None
        self.done_re = re.compile(progress["done_pattern"]) if "done_pattern" in progress else None
        self.ready_re = re.compile(progress["ready_pattern"]) if "ready_pattern" in progress else None
        self.lines = LineBuffer()
        self.last_step = 0
        self.ready = False
        self.done = False

    def feed(self, text: str, *, finalize: bool = False) -> list[_Event]:
        events: list[_Event] = []
        for line in self.lines.feed(text, finalize=finalize):
            event = self._line(line.strip())
            if event is not None:
                events.append(event)
        return events

    def _line(self, line: str) -> _Event | None:
        if self.ready_re is not None and not self.ready:
            match = self.ready_re.search(line)
            if match:
                self.ready = True
                return _Event("ready", fields={k: _number(v) for k, v in match.groupdict().items() if v is not None})
        if self.step_re is not None:
            match = self.step_re.search(line)
            if match:
                step = int(match.group("step"))
                if step <= self.last_step:
                    return None
                self.last_step = step
                fields = {
                    k: _number(v)
                    for k, v in match.groupdict().items()
                    if k != "step" and v is not None
                }
                return _Event("step", step=step, fields=fields)
        if self.done_re is not None and not self.done and self.done_re.search(line):
            self.done = True
            return _Event("done")
        return None

    def reset(self) -> None:
        self.lines.reset()
        self.last_step = 0
        self.ready = False
        self.done = False


class _Shared:
    """What both providers derive once from the contract and configuration."""

    def __init__(self, contract: Contract, config: Mapping[str, Any]) -> None:
        self.contract = contract
        self.config = dict(config)
        progress = contract.data["progress"]
        self.unit = progress["unit"]
        self.announces = progress.get("announces", "after-write")
        self.total = _positive_int(evaluate(progress.get("total"), self.config))
        self.output = contract.output(progress["output"]) if "output" in progress else None
        self.growing_view = self.view(growing=True) if self.output else None

    def view(self, *, growing: bool, output: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return self.contract.view_descriptor(output or self.output, self.config, growing=growing)

    def visible(self, step: int) -> int:
        """Steps a reader can open now. A line printed before the write lags by one."""
        return step if self.announces == "after-write" else step - 1


class ContractProgressAdapter:
    """RL40 progress: one record for each written step, with the output's view descriptor."""

    def __init__(self, contract: Contract, config: Mapping[str, Any]) -> None:
        self.shared = _Shared(contract, config)
        self.reader = _LineReader(contract, config)
        self.terminal = False

    @property
    def package(self) -> str:
        return self.shared.contract.pkg_type

    def observe_progress(self, text: str) -> list[ProgressObservation]:
        return self._observe(text, finalize=False)

    def finalize_progress(self) -> list[ProgressObservation]:
        observations = self._observe("", finalize=True)
        if self.reader.done and not self.terminal:
            observations.append(self._completed("application_reported_done"))
        return observations

    def finalize_progress_for_exit(self, return_code: int) -> list[ProgressObservation]:
        observations = self._observe("", finalize=True)
        if self.terminal:
            return observations
        if return_code == 0:
            observations.append(self._completed("process_exit_zero"))
        else:
            observations.append(self._failed(return_code))
        return observations

    def reset_progress(self) -> None:
        self.reader.reset()
        self.terminal = False

    def _observe(self, text: str, *, finalize: bool) -> list[ProgressObservation]:
        if self.terminal:
            return []
        observations = []
        for event in self.reader.feed(text, finalize=finalize):
            if event.kind == "step":
                observation = self._step(event)
            elif event.kind == "ready":
                observation = self._ready(event)
            else:
                observation = None
            if observation is not None:
                observations.append(observation)
        return observations

    def _step(self, event: _Event) -> ProgressObservation | None:
        shared = self.shared
        total = shared.total
        if total is not None and event.step > total:
            return None
        record: dict[str, Any] = {
            "schema": STEP_SCHEMA,
            "output": shared.output["name"],
            "step": event.step,
            "visible_steps": shared.visible(event.step),
            "fields": event.fields,
            "view": shared.growing_view,
        }
        if total is not None:
            record["expected_steps"] = total
        of_total = f" of {total}" if total is not None else ""
        return ProgressObservation(
            label="simulation",
            state=ProgressState.RUNNING,
            current=float(event.step),
            total=float(total) if total is not None else None,
            unit=shared.unit,
            message=f"{self.package} wrote {shared.unit} {event.step}{of_total} to {shared.output['name']}",
            metadata={"clio": record},
        )

    def _ready(self, event: _Event) -> ProgressObservation:
        service = self.shared.contract.service(self.shared.config)
        # A port chosen at launch (port 0 asks for a free one) is only known from the ready line.
        if "port" in event.fields and service["ports"]:
            service["ports"][0]["port"] = event.fields["port"]
        return ProgressObservation(
            label="service",
            state=ProgressState.READY,
            unit=self.shared.unit,
            message=f"{self.package} is ready",
            metadata={
                "clio": {
                    "schema": SERVICE_READY_SCHEMA,
                    "service": service,
                    "fields": event.fields,
                }
            },
        )

    def _completed(self, signal: str) -> ProgressObservation:
        self.terminal = True
        shared = self.shared
        metadata: dict[str, Any] = {"completion_signal": signal}
        if shared.output is not None:
            last = self.reader.last_step
            metadata["clio"] = {
                "schema": STEP_SCHEMA,
                "output": shared.output["name"],
                "step": last,
                "visible_steps": last,
                "view": shared.view(growing=False),
            }
            current = float(last)
            total = float(shared.total) if shared.total is not None else None
            if total is not None and current > total:
                current = total
            label = "simulation"
            message = f"{self.package} finished after {last} {shared.unit}s"
        else:
            current = total = None
            label = "service"
            message = f"{self.package} stopped"
        return ProgressObservation(
            label=label,
            state=ProgressState.COMPLETED,
            current=current,
            total=total,
            unit=shared.unit,
            message=message,
            metadata=metadata,
        )

    def _failed(self, return_code: int) -> ProgressObservation:
        self.terminal = True
        shared = self.shared
        total = float(shared.total) if shared.total is not None and shared.output else None
        current = float(min(self.reader.last_step, shared.total or self.reader.last_step)) if total else None
        return ProgressObservation(
            label="simulation" if shared.output else "service",
            state=ProgressState.FAILED,
            current=current,
            total=total,
            unit=shared.unit,
            message=f"{self.package} exited with status {return_code}",
            metadata={"completion_signal": "process_exit_nonzero", "return_code": return_code},
        )


def _tree_size(path: Path) -> int:
    # Sizes through an open descriptor: a stat() here can be stale when another node wrote the files.
    if path.is_file():
        return fresh_size(path)
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += fresh_size(Path(root) / name)
            except OSError:
                pass
    return total


class ContractArtifactAdapter:
    """RL40 outputs as jarvis-cd artifacts.

    Snapshots outputs carry their view descriptor and grow with each step.
    Statistics and restart outputs are reported once, when the run ends, if
    the run wrote them.
    """

    def __init__(self, contract: Contract, config: Mapping[str, Any]) -> None:
        self.shared = _Shared(contract, config)
        self.reader = _LineReader(contract, config)
        self.outputs = list(contract.data["outputs"])
        self.views = [output for output in self.outputs if is_view(output)]
        self.others = [output for output in self.outputs if not is_view(output)]
        self.ids = {output["name"]: new_artifact_id() for output in self.outputs}
        self.state: dict[str, ArtifactState] = {}
        self.terminal = False

    def observe_artifacts(self, text: str) -> list[ArtifactObservation]:
        return self._observe(text, finalize=False)

    def finalize_artifacts(self) -> list[ArtifactObservation]:
        return self._observe("", finalize=True)

    def finalize_artifacts_for_exit(self, return_code: int) -> list[ArtifactObservation]:
        observations = self._observe("", finalize=True)
        if self.terminal:
            return observations
        final = ArtifactState.FINALIZED if return_code == 0 else ArtifactState.INCOMPLETE
        written = [output for output in self.others if _exists(self._path(output), output["path_kind"])]
        if not self.state and not written:
            return observations
        self.terminal = True
        for output in self.views:
            if output["name"] not in self.state:
                continue
            path = Path(self._path(output))
            if final is ArtifactState.FINALIZED and not path.exists():
                state = ArtifactState.FAILED
            else:
                state = final
            size = _tree_size(path) if path.exists() else None
            observations.append(
                self._observation(output, state, growing=False, size=size, return_code=return_code)
            )
        for output in written:
            path = Path(self._path(output))
            size = _tree_size(path) if path.exists() else None
            observations.append(
                self._observation(output, final, growing=False, size=size, return_code=return_code)
            )
        return observations

    def reset_artifacts(self) -> None:
        self.reader.reset()
        self.state.clear()
        self.terminal = False

    def _observe(self, text: str, *, finalize: bool) -> list[ArtifactObservation]:
        if self.terminal:
            return []
        observations = []
        for event in self.reader.feed(text, finalize=finalize):
            if event.kind != "step":
                continue
            visible = self.shared.visible(event.step)
            for output in self.views:
                state = ArtifactState.AVAILABLE if visible >= 1 else ArtifactState.PRODUCING
                if self.state.get(output["name"]) is ArtifactState.AVAILABLE:
                    state = ArtifactState.AVAILABLE
                self.state[output["name"]] = state
                observations.append(
                    self._observation(output, state, growing=True, step=event.step, visible=visible)
                )
        return observations

    def _path(self, output: Mapping[str, Any]) -> str:
        if not is_view(output):
            return self.shared.contract.output_record(output, self.shared.config)["path"]
        return self.shared.view(growing=True, output=output)["path"]

    def _observation(
        self,
        output: Mapping[str, Any],
        state: ArtifactState,
        *,
        growing: bool,
        step: int | None = None,
        visible: int | None = None,
        size: int | None = None,
        return_code: int | None = None,
    ) -> ArtifactObservation:
        if is_view(output):
            view = self.shared.view(growing=growing, output=output)
            record: dict[str, Any] = {"view": view}
            location = view["path"]
        else:
            record = self.shared.contract.output_record(output, self.shared.config)
            location = record["path"]
        if step is not None:
            record["step"] = step
            record["visible_steps"] = visible
        if return_code is not None:
            record["return_code"] = return_code
        path = PurePosixPath(location)
        fmt = output["format"]
        return ArtifactObservation(
            artifact_id=self.ids[output["name"]],
            logical_name=output["name"],
            kind="scientific_dataset",
            role=_ROLES.get(output.get("role", VIEW_ROLE), ArtifactRole.OUTPUT),
            structure=_STRUCTURES[output["path_kind"]],
            ownership=ArtifactOwnership.SHARED,
            state=state,
            location=ArtifactLocation.cluster_path(path),
            media_type="application/x-adios2-bp" if fmt.startswith("adios2") else None,
            format=fmt,
            size_bytes=size,
            message=f"{output['name']}: {state.value}",
            metadata={"clio": record},
        )


def progress_adapter(pkg_dir: Path, package: Mapping[str, Any]) -> ContractProgressAdapter | None:
    contract = _contract_for(pkg_dir, package)
    return None if contract is None else ContractProgressAdapter(contract, package)


def artifact_adapter(pkg_dir: Path, package: Mapping[str, Any]) -> ContractArtifactAdapter | None:
    contract = _contract_for(pkg_dir, package)
    if contract is None or not contract.data["outputs"]:
        return None
    return ContractArtifactAdapter(contract, package)
