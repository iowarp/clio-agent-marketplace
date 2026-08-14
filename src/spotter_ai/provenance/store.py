"""SQLite-backed provenance store for the SPOTTER-AI pipeline.

Every pipeline stage execution, the artifacts it reads and writes, and the
run-level metrics it produces are recorded here so that a forensic-attribution
agent can later reconstruct exactly what happened in any run: which tool
version ran, what parameters and calibration it used, what it read and wrote,
and how those artifacts hash and summarize.

The store owns both the write path used by the campaign runner
(:func:`ProvenanceStore.begin_run`, :func:`ProvenanceStore.record_stage`, ...)
and the read path used by the FastMCP tool server (:func:`ProvenanceStore.list_runs`,
:func:`ProvenanceStore.get_run_health`, ...).

Forensic design note: an :class:`ArtifactRef` carries a ``role`` string. Roles
ending in ``"_config"`` mark artifacts that are external, campaign-level
configuration (currently only ``calibration.json``, fed into the ``calibrate``
stage) rather than per-run generated data. Per-run generated inputs (raw
sensor readings, a prior stage's own output) are *expected* to differ between
any two runs because each run is seeded independently -- that is not a
forensic anomaly. A ``"*_config"`` artifact, by contrast, is expected to be
byte-identical across every run of a healthy campaign, so any hash difference
there is forensically significant. This is the structural signal
:func:`ProvenanceStore.diff_stage_executions` uses to isolate genuine
tampering from ordinary run-to-run variation.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import statistics
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from spotter_ai import config

#: Parameter keys that are expected to vary per run by design (run identity,
#: not campaign configuration) and are therefore excluded from discrepancy
#: detection in :func:`ProvenanceStore.diff_stage_executions`.
IDENTITY_PARAM_KEYS = frozenset({"seed"})

#: Artifact-role suffix marking external, campaign-level configuration inputs
#: (as opposed to per-run generated data). See module docstring.
EXTERNAL_CONFIG_ROLE_SUFFIX = "_config"

#: Absolute floor applied to a baseline standard deviation before it is used
#: as a z-score denominator, so a metric with LITERALLY zero baseline
#: variance (or an empty/singleton baseline, see get_run_health) never
#: divides by zero. This alone is not enough to prevent a small-sample false
#: positive -- see RELATIVE_STD_FLOOR below.
MIN_BASELINE_STD = 1e-6

#: Floor on the baseline standard deviation, expressed as a FRACTION of the
#: baseline mean's magnitude rather than an absolute constant like
#: MIN_BASELINE_STD -- so it scales with each metric's own units instead of
#: being calibrated to one metric and meaningless for another (mean_biomass
#: and mean_height sit on very different scales). A small leave-one-out
#: baseline can land unusually TIGHT by pure sampling luck -- a low empirical
#: std that reflects sample-size noise, not the process actually being that
#: stable -- and dividing by that near-zero std manufactures an arbitrarily
#: large z for perfectly ordinary variation (observed: a 5-run campaign's
#: run-003 scored mean_height z=-6.46 against a 4-run baseline that happened
#: to be freakishly tight, #1218 r3). The synthetic pipeline's own healthy
#: run-to-run CV is ~1-3% (see pipeline.stages's module docstring); flooring
#: the std at 1% of the mean sits below that natural floor, so it damps
#: sampling noise in a small sample without masking a genuine deviation
#: (a real tamper shifts the mean by double digits, dwarfing a 1% floor).
RELATIVE_STD_FLOOR = 0.01

#: Minimum leave-one-out baseline sample size (the number of OTHER completed
#: runs a run's z-score is computed against) required before a verdict of
#: "normal"/"anomalous" is trusted. Statistical process control practice
#: (Shewhart/Western Electric control-chart convention) calls for a
#: substantial Phase I baseline -- commonly 20-25 historical subgroups --
#: before control limits computed from that history are considered
#: reliable; below that, the estimated standard deviation is itself so
#: noisy that an ordinary run can trip a large |z| from sampling luck alone
#: (exactly the run-003 false positive RELATIVE_STD_FLOOR's docstring
#: describes). 8 is a pragmatic floor for a live demo campaign, not the
#: textbook 20-25 -- well short of "reliable" in the SPC sense, but a
#: documented, principled minimum rather than trusting any n>=1 baseline.
#: Below this count, get_run_health reports "insufficient_baseline" instead
#: of a verdict the sample cannot statistically back.
MIN_BASELINE_SAMPLE = 8

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    campaign TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT
);

CREATE TABLE IF NOT EXISTS stage_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    tool_version TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    params_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256 TEXT NOT NULL,
    path TEXT NOT NULL,
    kind TEXT NOT NULL,
    summary_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS io (
    stage_execution_id INTEGER NOT NULL,
    artifact_id INTEGER NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('input', 'output')),
    role TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metrics (
    run_id TEXT NOT NULL,
    name TEXT NOT NULL,
    value REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_stage_executions_run ON stage_executions(run_id);
CREATE INDEX IF NOT EXISTS idx_io_stage_execution ON io(stage_execution_id);
CREATE INDEX IF NOT EXISTS idx_io_artifact ON io(artifact_id);
CREATE INDEX IF NOT EXISTS idx_metrics_run ON metrics(run_id);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name);
"""


def default_db_path() -> Path:
    """Resolve the provenance database path.

    Thin wrapper over :func:`spotter_ai.config.resolve_db_path` -- kept here
    (and re-exported from :mod:`spotter_ai.provenance`) for backward
    compatibility with existing callers/imports; the actual resolution logic
    lives in :mod:`spotter_ai.config` alongside campaign name and data
    directory resolution, since all three must agree with each other (see
    that module's docstring for why the database path is no longer resolved
    independently of the data directory).

    Returns:
        The path :func:`spotter_ai.config.resolve_db_path` resolves.
    """
    return config.resolve_db_path()


@dataclass(frozen=True)
class ArtifactRef:
    """A file reference passed to :func:`ProvenanceStore.record_stage`.

    Attributes:
        path: Filesystem path to the artifact file. Must exist and be
            readable at the time it is recorded.
        kind: Logical artifact type, e.g. ``"json"``.
        role: Forensic role of the artifact within the stage, e.g.
            ``"raw_readings"``, ``"calibration_config"``, ``"stage_output"``.
            See the module docstring for the ``"*_config"`` convention.
    """

    path: Path
    kind: str
    role: str


def _summarize_json(data: Any) -> dict[str, Any]:
    """Compute a small, bounded numeric summary of a parsed JSON artifact.

    Finds the first list-of-dicts collection in the payload (this pipeline's
    per-plant records) and reports its length plus the mean of each numeric
    field. If the payload carries a top-level ``"metrics"`` dict, its numeric
    values are folded into the summary too. The result is always small
    (a handful of scalars) regardless of the artifact's size.

    Args:
        data: Parsed JSON content (typically a dict).

    Returns:
        A bounded, JSON-serializable summary dict.
    """
    summary: dict[str, Any] = {}
    collection: list[Any] | None = None
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
                collection = value
                break

    if collection is not None:
        numeric_fields: dict[str, list[float]] = {}
        for record in collection:
            for key, val in record.items():
                if isinstance(val, int | float) and not isinstance(val, bool):
                    numeric_fields.setdefault(key, []).append(float(val))
        summary["count"] = len(collection)
        summary["means"] = {
            key: round(statistics.fmean(values), 6) for key, values in numeric_fields.items()
        }

    if isinstance(data, dict) and isinstance(data.get("metrics"), dict):
        summary["metrics"] = {
            key: val
            for key, val in data["metrics"].items()
            if isinstance(val, int | float) and not isinstance(val, bool)
        }

    return summary


def _summarize_artifact(path: Path, data: bytes) -> dict[str, Any]:
    """Build the bounded summary stored alongside an artifact's hash.

    Args:
        path: The artifact's filesystem path (used only for suffix sniffing).
        data: The artifact's raw file bytes.

    Returns:
        A bounded, JSON-serializable summary dict. JSON artifacts are
        summarized via :func:`_summarize_json`; anything else falls back to
        a byte-size summary.
    """
    if path.suffix == ".json":
        try:
            parsed = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {"byte_size": len(data)}
        return _summarize_json(parsed)
    return {"byte_size": len(data)}


class ProvenanceStore:
    """SQLite-backed recorder and query surface for pipeline provenance.

    A fresh connection is opened per call (SQLite handles this cheaply and it
    keeps the store safe to use from both the synchronous campaign CLI and
    the async FastMCP tool server without threading concerns).

    Args:
        db_path: Path to the SQLite database file. Defaults to
            :func:`default_db_path` (the ``SPOTTER_DB`` environment variable,
            or ``./spotter_provenance.sqlite``).
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else default_db_path()
        if self.db_path.parent != Path():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Open a short-lived connection, committing on success and always closing.

        Yields:
            A :class:`sqlite3.Connection` with ``row_factory`` set to
            :class:`sqlite3.Row`.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # -- write API -----------------------------------------------------

    def begin_run(self, run_id: str, campaign: str, started_at: str) -> None:
        """Record the start of a new run.

        Args:
            run_id: Unique run identifier, e.g. ``"run-001"``.
            campaign: Name of the campaign this run belongs to.
            started_at: ISO-8601 timestamp for when the run started.
        """
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO runs (run_id, campaign, status, started_at, ended_at) "
                "VALUES (?, ?, 'running', ?, NULL)",
                (run_id, campaign, started_at),
            )

    def end_run(self, run_id: str, status: Literal["completed", "failed"], ended_at: str) -> None:
        """Record the completion (success or failure) of a run.

        Args:
            run_id: The run to finalize.
            status: Final status, ``"completed"`` or ``"failed"``.
            ended_at: ISO-8601 timestamp for when the run ended.
        """
        with self._connect() as conn:
            conn.execute(
                "UPDATE runs SET status = ?, ended_at = ? WHERE run_id = ?",
                (status, ended_at, run_id),
            )

    def record_stage(
        self,
        run_id: str,
        stage: str,
        params: Mapping[str, Any],
        inputs: Iterable[ArtifactRef],
        outputs: Iterable[ArtifactRef],
        tool_version: str,
        started_at: str,
        ended_at: str,
    ) -> int:
        """Record one stage execution: its params plus every input/output artifact.

        Each artifact is content-hashed (sha256) and given a bounded summary
        at the moment it is recorded -- this is what lets forensic diffing
        later detect that, say, ``calibration.json`` had different content at
        the time the ``calibrate`` stage of one run read it versus another.

        Args:
            run_id: The run this stage execution belongs to.
            stage: Stage name, e.g. ``"calibrate"``.
            params: The stage's parameters (JSON-serialized as recorded).
            inputs: Artifacts the stage read.
            outputs: Artifacts the stage wrote.
            tool_version: Version identifier of the code that ran the stage.
            started_at: ISO-8601 timestamp for when the stage started.
            ended_at: ISO-8601 timestamp for when the stage ended.

        Returns:
            The new ``stage_executions.id``.
        """
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO stage_executions "
                "(run_id, stage, tool_version, started_at, ended_at, params_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    stage,
                    tool_version,
                    started_at,
                    ended_at,
                    json.dumps(dict(params), sort_keys=True),
                ),
            )
            stage_execution_id = cur.lastrowid
            assert stage_execution_id is not None
            for direction, refs in (("input", inputs), ("output", outputs)):
                for ref in refs:
                    artifact_id = self._insert_artifact(conn, ref)
                    conn.execute(
                        "INSERT INTO io (stage_execution_id, artifact_id, direction, role) "
                        "VALUES (?, ?, ?, ?)",
                        (stage_execution_id, artifact_id, direction, ref.role),
                    )
            return stage_execution_id

    def _insert_artifact(self, conn: sqlite3.Connection, ref: ArtifactRef) -> int:
        data = ref.path.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        summary = _summarize_artifact(ref.path, data)
        cur = conn.execute(
            "INSERT INTO artifacts (sha256, path, kind, summary_json) VALUES (?, ?, ?, ?)",
            (sha256, str(ref.path), ref.kind, json.dumps(summary)),
        )
        artifact_id = cur.lastrowid
        assert artifact_id is not None
        return artifact_id

    def record_metric(self, run_id: str, name: str, value: float) -> None:
        """Record one run-level metric value.

        Args:
            run_id: The run the metric belongs to.
            name: Metric name, e.g. ``"mean_biomass"``.
            value: Metric value.
        """
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO metrics (run_id, name, value) VALUES (?, ?, ?)",
                (run_id, name, value),
            )

    # -- read API --------------------------------------------------------

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Fetch a single run's header row.

        Args:
            run_id: The run to fetch.

        Returns:
            A dict with ``run_id``, ``campaign``, ``status``, ``started_at``,
            ``ended_at``, or ``None`` if no such run exists.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT run_id, campaign, status, started_at, ended_at FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def get_run_metrics(self, run_id: str) -> dict[str, float]:
        """Fetch all metric name/value pairs recorded for a run.

        Args:
            run_id: The run to fetch metrics for.

        Returns:
            A dict mapping metric name to value.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, value FROM metrics WHERE run_id = ?", (run_id,)
            ).fetchall()
            return {row["name"]: row["value"] for row in rows}

    def list_runs(self, campaign: str | None = None) -> list[dict[str, Any]]:
        """List runs (optionally filtered by campaign) with metrics and counts.

        Args:
            campaign: If given, only runs belonging to this campaign are
                returned. Otherwise all runs are returned.

        Returns:
            A list of dicts, one per run, each with ``run_id``, ``campaign``,
            ``status``, ``started_at``, ``ended_at``, ``metrics`` (dict),
            ``stage_count``, and ``artifact_count``. Ordered by ``run_id``.
        """
        with self._connect() as conn:
            query = "SELECT run_id, campaign, status, started_at, ended_at FROM runs"
            params: list[Any] = []
            if campaign is not None:
                query += " WHERE campaign = ?"
                params.append(campaign)
            query += " ORDER BY run_id"
            rows = conn.execute(query, params).fetchall()

            result = []
            for row in rows:
                run_id = row["run_id"]
                metric_rows = conn.execute(
                    "SELECT name, value FROM metrics WHERE run_id = ?", (run_id,)
                ).fetchall()
                stage_count = conn.execute(
                    "SELECT COUNT(*) FROM stage_executions WHERE run_id = ?", (run_id,)
                ).fetchone()[0]
                artifact_count = conn.execute(
                    "SELECT COUNT(DISTINCT io.artifact_id) FROM io "
                    "JOIN stage_executions se ON se.id = io.stage_execution_id "
                    "WHERE se.run_id = ?",
                    (run_id,),
                ).fetchone()[0]
                result.append(
                    {
                        "run_id": run_id,
                        "campaign": row["campaign"],
                        "status": row["status"],
                        "started_at": row["started_at"],
                        "ended_at": row["ended_at"],
                        "metrics": {r["name"]: r["value"] for r in metric_rows},
                        "stage_count": stage_count,
                        "artifact_count": artifact_count,
                    }
                )
            return result

    def totals(self) -> dict[str, int]:
        """Aggregate counts across the whole store.

        Returns:
            A dict with ``run_count``, ``stage_count``, ``artifact_count``.
        """
        with self._connect() as conn:
            run_count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            stage_count = conn.execute("SELECT COUNT(*) FROM stage_executions").fetchone()[0]
            artifact_count = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
            return {
                "run_count": run_count,
                "stage_count": stage_count,
                "artifact_count": artifact_count,
            }

    def get_metric_baseline(self, metric_name: str, exclude_run_id: str) -> list[float]:
        """Fetch a metric's values across every other completed run.

        Args:
            metric_name: The metric to gather.
            exclude_run_id: A run_id to exclude (typically the run under
                evaluation, so it does not contaminate its own baseline).

        Returns:
            The metric's values from all other completed runs.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT m.value FROM metrics m "
                "JOIN runs r ON r.run_id = m.run_id "
                "WHERE m.name = ? AND r.run_id != ? AND r.status = 'completed'",
                (metric_name, exclude_run_id),
            ).fetchall()
            return [row["value"] for row in rows]

    def get_run_health(self, run_id: str) -> list[dict[str, Any]]:
        """Compute a per-metric z-score for a run against all other completed runs.

        Args:
            run_id: The run to evaluate.

        Returns:
            A list of dicts, one per metric the run recorded, each with
            ``metric``, ``value``, ``baseline_mean``, ``baseline_std``,
            ``baseline_n`` (the leave-one-out baseline's sample size -- the
            count of OTHER completed runs this z-score was computed against),
            ``z``, and ``verdict``. ``z`` is always computed (even below the
            sample-size gate, so the number remains visible for context) but
            ``verdict`` is only ``"normal"``/``"anomalous"`` (``abs(z) < 3``
            or not) when ``baseline_n >= `` :data:`MIN_BASELINE_SAMPLE`;
            below that, ``verdict`` is ``"insufficient_baseline"`` --  there
            is not enough history yet to trust ANY z-score computed from it,
            no matter how large. The baseline standard deviation is floored
            at ``max(`` :data:`RELATIVE_STD_FLOOR` ``* abs(baseline_mean),``
            :data:`MIN_BASELINE_STD` ``)`` before being used as the z-score
            denominator, so a small baseline that happens to be freakishly
            tight cannot manufacture an arbitrarily large z on its own.
        """
        metrics = self.get_run_metrics(run_id)
        results = []
        for name, value in metrics.items():
            baseline = self.get_metric_baseline(name, exclude_run_id=run_id)
            baseline_n = len(baseline)
            if baseline_n >= 2:
                baseline_mean = statistics.fmean(baseline)
                baseline_std = statistics.stdev(baseline)
            elif baseline_n == 1:
                baseline_mean = baseline[0]
                baseline_std = 0.0
            else:
                baseline_mean = value
                baseline_std = 0.0
            floored_std = max(
                baseline_std, RELATIVE_STD_FLOOR * abs(baseline_mean), MIN_BASELINE_STD
            )
            z = (value - baseline_mean) / floored_std
            if baseline_n < MIN_BASELINE_SAMPLE:
                verdict = "insufficient_baseline"
            else:
                verdict = "normal" if abs(z) < 3 else "anomalous"
            results.append(
                {
                    "metric": name,
                    "value": value,
                    "baseline_mean": baseline_mean,
                    "baseline_std": baseline_std,
                    "baseline_n": baseline_n,
                    "z": z,
                    "verdict": verdict,
                }
            )
        return results

    def list_stage_executions(self, run_id: str, stage: str | None = None) -> list[dict[str, Any]]:
        """List a run's stage executions with their input/output artifacts.

        Args:
            run_id: The run to list stage executions for.
            stage: If given, only this stage's execution is returned.

        Returns:
            A list of dicts ordered by execution id (pipeline order), each
            with ``stage_execution_id``, ``stage``, ``tool_version``,
            ``started_at``, ``ended_at``, ``params``, ``inputs``, ``outputs``.
            ``inputs``/``outputs`` are lists of dicts with ``artifact_id``,
            ``sha256``, ``path``, ``kind``, ``role``, ``summary``.
        """
        with self._connect() as conn:
            query = "SELECT * FROM stage_executions WHERE run_id = ?"
            params: list[Any] = [run_id]
            if stage is not None:
                query += " AND stage = ?"
                params.append(stage)
            query += " ORDER BY id"
            rows = conn.execute(query, params).fetchall()

            result = []
            for row in rows:
                io_rows = conn.execute(
                    "SELECT io.direction, io.role, a.id AS artifact_id, a.sha256, a.path, "
                    "a.kind, a.summary_json "
                    "FROM io JOIN artifacts a ON a.id = io.artifact_id "
                    "WHERE io.stage_execution_id = ? ORDER BY a.id",
                    (row["id"],),
                ).fetchall()
                inputs = []
                outputs = []
                for io_row in io_rows:
                    entry = {
                        "artifact_id": io_row["artifact_id"],
                        "sha256": io_row["sha256"],
                        "path": io_row["path"],
                        "kind": io_row["kind"],
                        "role": io_row["role"],
                        "summary": json.loads(io_row["summary_json"]),
                    }
                    (inputs if io_row["direction"] == "input" else outputs).append(entry)
                result.append(
                    {
                        "stage_execution_id": row["id"],
                        "stage": row["stage"],
                        "tool_version": row["tool_version"],
                        "started_at": row["started_at"],
                        "ended_at": row["ended_at"],
                        "params": json.loads(row["params_json"]),
                        "inputs": inputs,
                        "outputs": outputs,
                    }
                )
            return result

    def trace_lineage(self, run_id: str, stage: str | None = None) -> list[dict[str, Any]]:
        """Trace a run's stage executions backward from its last stage (or a given one).

        Args:
            run_id: The run to trace.
            stage: If given, the chain starts at this stage and walks backward
                through only its ancestors (stages that ran at or before it),
                excluding any stage that ran after it. If omitted, the full
                pipeline is traced backward from its last stage.

        Returns:
            Stage execution dicts (same shape as
            :func:`list_stage_executions`) ordered from most recent to
            earliest -- i.e. tracing an output back to its origin.

        Raises:
            ValueError: If the run has no recorded stage executions, or if
                ``stage`` does not appear among them.
        """
        executions = self.list_stage_executions(run_id)
        if not executions:
            raise ValueError(f"no stage executions recorded for run_id={run_id!r}")
        if stage is not None:
            matches = [e for e in executions if e["stage"] == stage]
            if not matches:
                raise ValueError(f"stage {stage!r} not found for run_id={run_id!r}")
            cutoff_id = matches[0]["stage_execution_id"]
            executions = [e for e in executions if e["stage_execution_id"] <= cutoff_id]
        return list(reversed(executions))

    def get_artifact(self, artifact_id: int) -> dict[str, Any] | None:
        """Fetch one artifact's metadata by id.

        Args:
            artifact_id: The artifact's ``artifacts.id``.

        Returns:
            A dict with ``id``, ``sha256``, ``path``, ``kind``, ``summary``,
            or ``None`` if no such artifact exists.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, sha256, path, kind, summary_json FROM artifacts WHERE id = ?",
                (artifact_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "id": row["id"],
                "sha256": row["sha256"],
                "path": row["path"],
                "kind": row["kind"],
                "summary": json.loads(row["summary_json"]),
            }

    def diff_stage_executions(self, run_id: str, baseline_run_id: str) -> dict[str, Any]:
        """Compare two runs stage-by-stage and isolate forensic discrepancies.

        For each stage present in both runs, compares params (excluding
        :data:`IDENTITY_PARAM_KEYS`), tool_version, and the hashes of any
        input artifact whose role marks it as external configuration (role
        ending in ``"_config"`` -- see the module docstring). Output artifact
        summaries are always diffed and reported as informational deltas,
        never as discrepancies, since per-run generated data is expected to
        differ.

        Args:
            run_id: The run under evaluation.
            baseline_run_id: The run to compare it against.

        Returns:
            A dict with ``run_id``, ``baseline_run_id``, ``stages`` (a list of
            per-stage comparison dicts with ``stage``, ``params_equal``,
            ``input_hashes_equal``, ``tool_version_equal``,
            ``output_summary_deltas``), and ``discrepancies`` (a list of
            ``{"stage", "kind", "detail"}`` dicts capturing only the
            forensically significant differences).
        """
        run_stages = {s["stage"]: s for s in self.list_stage_executions(run_id)}
        baseline_stages = {s["stage"]: s for s in self.list_stage_executions(baseline_run_id)}

        stages_out = []
        discrepancies = []
        for stage_name in sorted(set(run_stages) & set(baseline_stages)):
            run_exec = run_stages[stage_name]
            base_exec = baseline_stages[stage_name]

            params_equal = self._params_equal(
                stage_name, run_exec["params"], base_exec["params"], discrepancies
            )

            input_hashes_equal = self._input_hashes_equal(
                stage_name, run_exec["inputs"], base_exec["inputs"], discrepancies
            )

            tool_version_equal = run_exec["tool_version"] == base_exec["tool_version"]
            if not tool_version_equal:
                discrepancies.append(
                    {
                        "stage": stage_name,
                        "kind": "tool_version_mismatch",
                        "detail": f"{run_exec['tool_version']!r} != {base_exec['tool_version']!r}",
                    }
                )

            output_summary_deltas = self._output_summary_deltas(
                run_exec["outputs"], base_exec["outputs"]
            )

            stages_out.append(
                {
                    "stage": stage_name,
                    "params_equal": params_equal,
                    "input_hashes_equal": input_hashes_equal,
                    "tool_version_equal": tool_version_equal,
                    "output_summary_deltas": output_summary_deltas,
                }
            )

        return {
            "run_id": run_id,
            "baseline_run_id": baseline_run_id,
            "stages": stages_out,
            "discrepancies": discrepancies,
        }

    @staticmethod
    def _params_equal(
        stage: str,
        run_params: Mapping[str, Any],
        base_params: Mapping[str, Any],
        discrepancies: list[dict[str, Any]],
    ) -> bool:
        equal = True
        for key in sorted(set(run_params) | set(base_params)):
            if key in IDENTITY_PARAM_KEYS:
                continue
            run_value = run_params.get(key)
            base_value = base_params.get(key)
            if run_value != base_value:
                equal = False
                discrepancies.append(
                    {
                        "stage": stage,
                        "kind": "param_mismatch",
                        "detail": f"{key}: {run_value!r} != {base_value!r}",
                    }
                )
        return equal

    @staticmethod
    def _input_hashes_equal(
        stage: str,
        run_inputs: list[dict[str, Any]],
        base_inputs: list[dict[str, Any]],
        discrepancies: list[dict[str, Any]],
    ) -> bool:
        run_by_role = {i["role"]: i for i in run_inputs}
        base_by_role = {i["role"]: i for i in base_inputs}
        equal = True
        for role in sorted(set(run_by_role) & set(base_by_role)):
            run_hash = run_by_role[role]["sha256"]
            base_hash = base_by_role[role]["sha256"]
            if run_hash == base_hash:
                continue
            equal = False
            if role.endswith(EXTERNAL_CONFIG_ROLE_SUFFIX):
                discrepancies.append(
                    {
                        "stage": stage,
                        "kind": "input_hash_mismatch",
                        "detail": f"{role}: {run_hash[:12]}... != {base_hash[:12]}...",
                    }
                )
        return equal

    @staticmethod
    def _output_summary_deltas(
        run_outputs: list[dict[str, Any]], base_outputs: list[dict[str, Any]]
    ) -> dict[str, dict[str, float]]:
        run_by_role = {o["role"]: o for o in run_outputs}
        base_by_role = {o["role"]: o for o in base_outputs}
        deltas: dict[str, dict[str, float]] = {}
        for role in sorted(set(run_by_role) & set(base_by_role)):
            run_means = run_by_role[role]["summary"].get("means", {})
            base_means = base_by_role[role]["summary"].get("means", {})
            role_deltas = {
                field: round(run_means[field] - base_means[field], 6)
                for field in run_means
                if field in base_means
            }
            if role_deltas:
                deltas[role] = role_deltas
        return deltas
