"""Focused forensic-store behavior tests."""

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from spotter_ai.campaign import CampaignConfig, CampaignForensics
from spotter_ai.errors import ProvenanceError


def _store(tmp_path: Path) -> CampaignForensics:
    database = tmp_path / "campaign.sqlite"
    artifact = tmp_path / "calibration.json"
    artifact.write_text('{"scale": 1.0}', encoding="utf-8")
    altered = tmp_path / "calibration-tampered.json"
    altered.write_text('{"scale": 9.0}', encoding="utf-8")
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE runs (
            run_id TEXT PRIMARY KEY, campaign TEXT NOT NULL, status TEXT NOT NULL,
            started_at TEXT NOT NULL, ended_at TEXT
        );
        CREATE TABLE stage_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, stage TEXT NOT NULL,
            tool_version TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT NOT NULL,
            params_json TEXT NOT NULL
        );
        CREATE TABLE artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, sha256 TEXT NOT NULL, path TEXT NOT NULL,
            kind TEXT NOT NULL, summary_json TEXT NOT NULL
        );
        CREATE TABLE io (
            stage_execution_id INTEGER NOT NULL, artifact_id INTEGER NOT NULL,
            direction TEXT NOT NULL, role TEXT NOT NULL
        );
        CREATE TABLE metrics (run_id TEXT NOT NULL, name TEXT NOT NULL, value REAL NOT NULL);
        """
    )
    for index, path in ((1, artifact), (2, altered)):
        run_id = f"run-{index:03d}"
        connection.execute(
            "INSERT INTO runs VALUES (?, 'phenotype-2026', 'completed', 'start', 'end')",
            (run_id,),
        )
        cursor = connection.execute(
            "INSERT INTO stage_executions "
            "(run_id, stage, tool_version, started_at, ended_at, params_json) "
            "VALUES (?, 'calibrate', '1.0', 'start', 'end', ?)",
            (run_id, json.dumps({"seed": index, "mode": "reference"})),
        )
        content = path.read_bytes()
        artifact_cursor = connection.execute(
            "INSERT INTO artifacts (sha256, path, kind, summary_json) VALUES (?, ?, 'json', ?)",
            (hashlib.sha256(content).hexdigest(), str(path), json.dumps({"scale": index})),
        )
        connection.execute(
            "INSERT INTO io VALUES (?, ?, 'input', 'calibration_config')",
            (cursor.lastrowid, artifact_cursor.lastrowid),
        )
    connection.commit()
    connection.close()
    return CampaignForensics(CampaignConfig("phenotype-2026", database, tmp_path / "data"))


def test_diff_preserves_tampered_configuration_relationship(tmp_path: Path) -> None:
    """Run comparison exposes the altered config hash rather than collapsing it."""
    store = _store(tmp_path)

    result = store.diff_runs("run-002", "run-001")

    assert result["stages"][0]["params_equal"] is True
    assert result["stages"][0]["input_config_hashes_equal"] is False
    assert result["discrepancies"][0]["kind"] == "input_config_hash"


def test_trace_and_read_keep_exact_artifact_evidence(tmp_path: Path) -> None:
    """Lineage returns the persisted node and reading returns its exact content."""
    store = _store(tmp_path)

    trace = store.trace_lineage("run-002")
    artifact_id = trace["chain"][0]["inputs"][0]["artifact_id"]
    artifact = store.read_artifact(artifact_id)

    assert trace["chain"][0]["stage"] == "calibrate"
    assert artifact["content"] == '{"scale": 9.0}'


def test_missing_database_is_typed_and_never_created(tmp_path: Path) -> None:
    """Absent campaign storage fails visibly without fabricating an empty store."""
    database = tmp_path / "missing.sqlite"
    store = CampaignForensics(CampaignConfig("phenotype-2026", database, tmp_path / "data"))

    with pytest.raises(ProvenanceError, match="does not exist") as error:
        store.list_runs()

    assert error.value.code == "campaign_store_unavailable"
    assert not database.exists()
