"""Phenotype campaign forensics layered beside provider-aware provenance.

The reference phenotype workload records a compact SQLite provenance graph and
uses a ``QUARANTINE`` sentinel to stop between runs.  This module reads that
existing contract without importing the workload package, so the SPOTTER pack
remains independently installable while still exposing the containment tools
that made the original forensic watcher useful.
"""

from __future__ import annotations

import json
import os
import sqlite3
import statistics
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from spotter_ai.errors import ProvenanceError

MIN_BASELINE_SAMPLE = 8
MIN_BASELINE_STD = 1e-6
RELATIVE_STD_FLOOR = 0.01
QUARANTINE_FILENAME = "QUARANTINE"
READ_ARTIFACT_CONTENT_CAP = 4000
_REQUIRED_TABLES = frozenset({"runs", "stage_executions", "artifacts", "io", "metrics"})


@dataclass(frozen=True)
class CampaignConfig:
    """Fixed paths and identity for one watched phenotype campaign."""

    campaign: str
    database_path: Path
    data_directory: Path

    @classmethod
    def from_environment(cls) -> CampaignConfig:
        """Resolve the campaign contract from the workload's shared variables."""
        data_directory = Path(os.environ.get("SPOTTER_DATA_DIR", "./campaign_data")).resolve()
        database_value = os.environ.get("SPOTTER_DB", "").strip()
        database_path = (
            Path(database_value).resolve()
            if database_value
            else data_directory.parent / "spotter_provenance.sqlite"
        )
        return cls(
            campaign=os.environ.get("SPOTTER_CAMPAIGN", "phenotype-2026"),
            database_path=database_path,
            data_directory=data_directory,
        )


class CampaignForensics:
    """Read and contain one phenotype campaign without owning its write path."""

    def __init__(self, config: CampaignConfig | None = None) -> None:
        """Bind campaign paths once for the lifetime of an MCP server."""
        self.config = config or CampaignConfig.from_environment()

    def capabilities(self) -> dict[str, Any]:
        """Describe availability without creating a missing SQLite database."""
        try:
            with self._connect() as connection:
                self._require_schema(connection)
        except ProvenanceError as exc:
            return {
                "provider": "phenotype_sqlite",
                "status": "unavailable",
                "reason": exc.code,
                "database_path": str(self.config.database_path),
                "campaign": self.config.campaign,
                "capabilities": [],
            }
        return {
            "provider": "phenotype_sqlite",
            "status": "ready",
            "database_path": str(self.config.database_path),
            "campaign": self.config.campaign,
            "capabilities": [
                "list_runs",
                "run_health",
                "campaign_health",
                "diff_runs",
                "trace_lineage",
                "read_artifact",
                "raise_alert",
                "lift_quarantine",
            ],
        }

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        path = self.config.database_path
        if not path.is_file():
            raise ProvenanceError(
                code="campaign_store_unavailable",
                message=f"phenotype provenance database does not exist: {path}",
                details={"path": str(path), "campaign": self.config.campaign},
            )
        try:
            connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        except sqlite3.Error as exc:
            raise ProvenanceError(
                code="campaign_store_unavailable",
                message=f"could not open phenotype provenance database: {exc}",
                details={"path": str(path), "campaign": self.config.campaign},
            ) from exc
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    def _require_schema(self, connection: sqlite3.Connection) -> None:
        try:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        except sqlite3.Error as exc:
            raise ProvenanceError(
                code="campaign_store_invalid",
                message=f"could not inspect phenotype provenance schema: {exc}",
                details={"path": str(self.config.database_path)},
            ) from exc
        missing = sorted(_REQUIRED_TABLES - {str(row["name"]) for row in rows})
        if missing:
            raise ProvenanceError(
                code="campaign_store_invalid",
                message="phenotype provenance database is missing required tables",
                details={"path": str(self.config.database_path), "missing": missing},
            )

    def _run(self, run_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            self._require_schema(connection)
            row = connection.execute(
                "SELECT run_id, campaign, status, started_at, ended_at FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise ProvenanceError(
                code="campaign_run_not_found",
                message=f"phenotype run {run_id!r} was not found",
                details={"run_id": run_id, "campaign": self.config.campaign},
            )
        return dict(row)

    def list_runs(self) -> dict[str, Any]:
        """Return campaign-scoped runs with metrics and graph cardinality."""
        with self._connect() as connection:
            self._require_schema(connection)
            rows = connection.execute(
                "SELECT run_id, campaign, status, started_at, ended_at FROM runs "
                "WHERE campaign = ? ORDER BY run_id",
                (self.config.campaign,),
            ).fetchall()
            runs: list[dict[str, Any]] = []
            for row in rows:
                run_id = str(row["run_id"])
                metrics = connection.execute(
                    "SELECT name, value FROM metrics WHERE run_id = ? ORDER BY name", (run_id,)
                ).fetchall()
                stage_count = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM stage_executions WHERE run_id = ?", (run_id,)
                    ).fetchone()[0]
                )
                artifact_count = int(
                    connection.execute(
                        "SELECT COUNT(DISTINCT io.artifact_id) FROM io "
                        "JOIN stage_executions se ON se.id = io.stage_execution_id "
                        "WHERE se.run_id = ?",
                        (run_id,),
                    ).fetchone()[0]
                )
                runs.append(
                    {
                        **dict(row),
                        "metrics": {str(metric["name"]): metric["value"] for metric in metrics},
                        "stage_count": stage_count,
                        "artifact_count": artifact_count,
                    }
                )
            totals = {
                "run_count": int(connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0]),
                "stage_count": int(
                    connection.execute("SELECT COUNT(*) FROM stage_executions").fetchone()[0]
                ),
                "artifact_count": int(
                    connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
                ),
            }
        return {"campaign": self.config.campaign, "runs": runs, "totals": totals}

    def run_health(self, run_id: str) -> dict[str, Any]:
        """Score a run against completed peers using the workload's stable formula."""
        self._run(run_id)
        with self._connect() as connection:
            metrics = connection.execute(
                "SELECT name, value FROM metrics WHERE run_id = ? ORDER BY name", (run_id,)
            ).fetchall()
            results: list[dict[str, Any]] = []
            for metric in metrics:
                name = str(metric["name"])
                value = float(metric["value"])
                baseline_rows = connection.execute(
                    "SELECT m.value FROM metrics m JOIN runs r ON r.run_id = m.run_id "
                    "WHERE m.name = ? AND r.run_id != ? AND r.status = 'completed'",
                    (name, run_id),
                ).fetchall()
                baseline = [float(row["value"]) for row in baseline_rows]
                mean = statistics.fmean(baseline) if baseline else value
                standard_deviation = statistics.stdev(baseline) if len(baseline) >= 2 else 0.0
                denominator = max(
                    standard_deviation, RELATIVE_STD_FLOOR * abs(mean), MIN_BASELINE_STD
                )
                score = (value - mean) / denominator
                verdict = (
                    "insufficient_baseline"
                    if len(baseline) < MIN_BASELINE_SAMPLE
                    else "normal"
                    if abs(score) < 3
                    else "anomalous"
                )
                results.append(
                    {
                        "metric": name,
                        "value": value,
                        "baseline_mean": mean,
                        "baseline_std": standard_deviation,
                        "baseline_n": len(baseline),
                        "z": score,
                        "verdict": verdict,
                    }
                )
        return {"run_id": run_id, "metrics": results}

    def campaign_health(self) -> dict[str, Any]:
        """Evaluate every completed run and return one bounded verdict per run."""
        runs = self.list_runs()["runs"]
        verdicts: list[dict[str, Any]] = []
        for run in runs:
            if run["status"] != "completed":
                continue
            health = self.run_health(str(run["run_id"]))["metrics"]
            if not health:
                continue
            worst = max(health, key=lambda row: abs(float(row["z"])))
            verdicts.append(
                {
                    "run_id": run["run_id"],
                    "verdict": worst["verdict"],
                    "worst_metric": worst["metric"],
                    "worst_z": worst["z"],
                    "value": worst["value"],
                    "baseline_mean": worst["baseline_mean"],
                    "baseline_n": worst["baseline_n"],
                }
            )
        return {
            "campaign": self.config.campaign,
            "runs_checked": len(verdicts),
            "verdicts": verdicts,
            "anomalous": [str(row["run_id"]) for row in verdicts if row["verdict"] == "anomalous"],
        }

    def _stage_executions(self, run_id: str) -> list[dict[str, Any]]:
        self._run(run_id)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM stage_executions WHERE run_id = ? ORDER BY id", (run_id,)
            ).fetchall()
            executions: list[dict[str, Any]] = []
            for row in rows:
                io_rows = connection.execute(
                    "SELECT io.direction, io.role, a.id AS artifact_id, a.sha256, a.path, "
                    "a.kind, a.summary_json FROM io JOIN artifacts a ON a.id = io.artifact_id "
                    "WHERE io.stage_execution_id = ? ORDER BY a.id",
                    (row["id"],),
                ).fetchall()
                inputs: list[dict[str, Any]] = []
                outputs: list[dict[str, Any]] = []
                for item in io_rows:
                    projected = {
                        "artifact_id": item["artifact_id"],
                        "sha256": item["sha256"],
                        "path": item["path"],
                        "kind": item["kind"],
                        "role": item["role"],
                        "summary": json.loads(item["summary_json"]),
                    }
                    (inputs if item["direction"] == "input" else outputs).append(projected)
                executions.append(
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
        return executions

    def trace_lineage(self, run_id: str, stage: str | None = None) -> dict[str, Any]:
        """Return the recorded stage chain newest-first, optionally from one stage."""
        executions = self._stage_executions(run_id)
        if stage is not None:
            matches = [row for row in executions if row["stage"] == stage]
            if not matches:
                raise ProvenanceError(
                    code="campaign_stage_not_found",
                    message=f"stage {stage!r} was not found for phenotype run {run_id!r}",
                    details={"run_id": run_id, "stage": stage},
                )
            cutoff = int(matches[0]["stage_execution_id"])
            executions = [row for row in executions if int(row["stage_execution_id"]) <= cutoff]
        return {"run_id": run_id, "stage_filter": stage, "chain": list(reversed(executions))}

    def diff_runs(self, run_id: str, baseline_run_id: str) -> dict[str, Any]:
        """Compare matched stages and preserve every discrepancy instead of summarizing it away."""
        current = {row["stage"]: row for row in self._stage_executions(run_id)}
        baseline = {row["stage"]: row for row in self._stage_executions(baseline_run_id)}
        stages: list[dict[str, Any]] = []
        discrepancies: list[dict[str, Any]] = []
        for stage in sorted(current.keys() | baseline.keys()):
            left = current.get(stage)
            right = baseline.get(stage)
            if left is None or right is None:
                detail = "stage missing from run" if left is None else "stage missing from baseline"
                discrepancies.append({"stage": stage, "kind": "stage_missing", "detail": detail})
                continue
            left_params = {key: value for key, value in left["params"].items() if key != "seed"}
            right_params = {key: value for key, value in right["params"].items() if key != "seed"}
            left_configs = {
                str(item["role"]): str(item["sha256"])
                for item in left["inputs"]
                if str(item["role"]).endswith("_config")
            }
            right_configs = {
                str(item["role"]): str(item["sha256"])
                for item in right["inputs"]
                if str(item["role"]).endswith("_config")
            }
            row = {
                "stage": stage,
                "params_equal": left_params == right_params,
                "input_config_hashes_equal": left_configs == right_configs,
                "tool_version_equal": left["tool_version"] == right["tool_version"],
                "run_params": left_params,
                "baseline_params": right_params,
                "run_config_hashes": left_configs,
                "baseline_config_hashes": right_configs,
            }
            stages.append(row)
            for key, kind in (
                ("params_equal", "params"),
                ("input_config_hashes_equal", "input_config_hash"),
                ("tool_version_equal", "tool_version"),
            ):
                if not row[key]:
                    discrepancies.append(
                        {
                            "stage": stage,
                            "kind": kind,
                            "detail": {k: v for k, v in row.items() if k != "stage"},
                        }
                    )
        return {
            "run_id": run_id,
            "baseline_run_id": baseline_run_id,
            "stages": stages,
            "discrepancies": discrepancies,
        }

    def read_artifact(self, artifact_id: int) -> dict[str, Any]:
        """Read one exact recorded artifact with bounded text content."""
        with self._connect() as connection:
            self._require_schema(connection)
            row = connection.execute(
                "SELECT id, sha256, path, kind, summary_json FROM artifacts WHERE id = ?",
                (artifact_id,),
            ).fetchone()
        if row is None:
            raise ProvenanceError(
                code="campaign_artifact_not_found",
                message=f"phenotype artifact {artifact_id} was not found",
                details={"artifact_id": artifact_id},
            )
        path = Path(str(row["path"]))
        if not path.is_file():
            raise ProvenanceError(
                code="campaign_artifact_unavailable",
                message=f"phenotype artifact path does not exist: {path}",
                details={"artifact_id": artifact_id, "path": str(path)},
            )
        return {
            "artifact_id": artifact_id,
            "path": str(path),
            "sha256": row["sha256"],
            "kind": row["kind"],
            "summary": json.loads(row["summary_json"]),
            "content": path.read_text(encoding="utf-8", errors="replace")[
                :READ_ARTIFACT_CONTENT_CAP
            ],
        }

    def raise_alert(self, run_id: str, reason: str) -> dict[str, Any]:
        """Validate the implicated run, then atomically quarantine the campaign."""
        self._run(run_id)
        timestamp = datetime.now(UTC).isoformat()
        path = self.config.data_directory / QUARANTINE_FILENAME
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            f"run_id: {run_id}\nreason: {reason}\ntimestamp: {timestamp}\n", encoding="utf-8"
        )
        temporary.replace(path)
        return {
            "quarantined": True,
            "path": str(path),
            "run_id": run_id,
            "reason": reason,
            "timestamp": timestamp,
        }

    def lift_quarantine(self) -> dict[str, Any]:
        """Remove the shared sentinel after explicit human authorization."""
        path = self.config.data_directory / QUARANTINE_FILENAME
        existed = path.is_file()
        if existed:
            path.unlink()
        return {"lifted": existed, "path": str(path)}


def validate_reason(reason: str) -> str:
    """Reject blank containment reasons before writing a sentinel."""
    resolved = reason.strip()
    if not resolved:
        raise ProvenanceError(
            code="campaign_alert_invalid",
            message="an anomaly alert requires a non-empty evidence-backed reason",
        )
    return resolved


def stable_tool_annotations(*, read_only: bool) -> dict[str, bool]:
    """Return consistent FastMCP annotations for campaign tools."""
    return {
        "readOnlyHint": read_only,
        "destructiveHint": not read_only,
        "idempotentHint": read_only,
        "openWorldHint": False,
    }
