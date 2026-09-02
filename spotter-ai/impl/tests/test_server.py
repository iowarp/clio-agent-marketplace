"""FastMCP contract tests for the provider-aware Spotter surface."""

import json
import sqlite3
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from spotter_ai.campaign import CampaignConfig, CampaignForensics
from spotter_ai.config import NativeQueryConfig
from spotter_ai.providers.jsonl import JsonlProvider
from spotter_ai.server import create_server
from spotter_ai.service import ProvenanceService


@pytest.fixture
def native_server(tmp_path: Path):
    """Create a server backed by one real native provider."""
    journal = tmp_path / "events.jsonl"
    journal.write_text(
        json.dumps(
            {
                "event_type": "lm.completed",
                "event_id": "event-1",
                "session_id": "session-1",
                "trace_id": "campaign-1",
                "turn_id": "turn-1",
                "occurred_at": "2026-08-22T12:00:00Z",
                "actor": {"agent_id": "agent-1"},
                "payload": {"correlation_id": "correlation-1"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    provider = JsonlProvider(NativeQueryConfig(journal, tmp_path))
    database = tmp_path / "campaign.sqlite"
    _seed_campaign(database)
    campaign = CampaignForensics(CampaignConfig("phenotype-2026", database, tmp_path / "data"))
    return create_server(service=ProvenanceService(provider, provider), campaign=campaign)


def _seed_campaign(database: Path) -> None:
    """Create the workload's real SQLite shape with a statistically useful campaign."""
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE runs (
            run_id TEXT PRIMARY KEY,
            campaign TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT
        );
        CREATE TABLE stage_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            tool_version TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT NOT NULL,
            params_json TEXT NOT NULL
        );
        CREATE TABLE artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sha256 TEXT NOT NULL,
            path TEXT NOT NULL,
            kind TEXT NOT NULL,
            summary_json TEXT NOT NULL
        );
        CREATE TABLE io (
            stage_execution_id INTEGER NOT NULL,
            artifact_id INTEGER NOT NULL,
            direction TEXT NOT NULL,
            role TEXT NOT NULL
        );
        CREATE TABLE metrics (run_id TEXT NOT NULL, name TEXT NOT NULL, value REAL NOT NULL);
        """
    )
    for index in range(1, 13):
        run_id = f"run-{index:03d}"
        connection.execute(
            "INSERT INTO runs VALUES (?, 'phenotype-2026', 'completed', ?, ?)",
            (run_id, "2026-08-28T00:00:00Z", "2026-08-28T00:00:01Z"),
        )
        value = 175.0 if index == 12 else 100.0 + (index % 3)
        connection.execute("INSERT INTO metrics VALUES (?, 'mean_biomass', ?)", (run_id, value))
    connection.commit()
    connection.close()


async def test_exposes_purpose_specific_tools_without_provider_arguments(native_server) -> None:
    """The agent selects a question, while configuration selects providers."""
    async with Client(native_server) as client:
        tools = await client.list_tools()

    names = {tool.name for tool in tools}
    assert names == {
        "capabilities",
        "list_campaigns",
        "list_workflows",
        "list_agents",
        "query_tasks",
        "summarize_tasks",
        "get_timeline",
        "list_pipelines",
        "list_executions",
        "list_artifact_types",
        "list_artifacts",
        "get_execution_lineage",
        "get_artifact_lineage",
        "get_model_card",
        "trace_correlation",
        "list_runs",
        "run_health",
        "campaign_health",
        "diff_runs",
        "trace_lineage",
        "read_artifact",
        "raise_alert",
        "lift_quarantine",
    }
    for tool in tools:
        assert "provider" not in tool.inputSchema.get("properties", {})
        assert tool.annotations is not None
        if tool.name in {"raise_alert", "lift_quarantine"}:
            assert tool.annotations.readOnlyHint is False
            assert tool.annotations.destructiveHint is True
            assert tool.annotations.idempotentHint is False
            assert tool.annotations.openWorldHint is False
        else:
            assert tool.annotations.readOnlyHint is True
            assert tool.annotations.destructiveHint is False
            assert tool.annotations.idempotentHint is True


async def test_capabilities_name_the_active_providers(native_server) -> None:
    """Capability discovery reports both independent provider domains."""
    async with Client(native_server) as client:
        result = await client.call_tool("capabilities", {})

    assert result.data["agentic"]["provider"] == "native"
    assert result.data["artifact"]["provider"] == "native"
    assert "get_timeline" in result.data["agentic"]["capabilities"]
    assert "list_pipelines" not in result.data["artifact"]["capabilities"]
    assert result.data["campaign_forensics"]["status"] == "ready"
    assert "campaign_health" in result.data["campaign_forensics"]["capabilities"]


async def test_campaign_health_detects_injected_outlier(native_server) -> None:
    """The reference run-012 injection is visible to the restored watcher surface."""
    async with Client(native_server) as client:
        result = await client.call_tool("campaign_health", {})

    assert result.data["runs_checked"] == 12
    assert result.data["anomalous"] == ["run-012"]
    run = next(row for row in result.data["verdicts"] if row["run_id"] == "run-012")
    assert run["worst_metric"] == "mean_biomass"
    assert run["worst_z"] > 5


async def test_alert_quarantines_and_explicit_lift_resumes(native_server, tmp_path: Path) -> None:
    """Human review durably acknowledges an anomaly and prevents re-quarantine."""
    async with Client(native_server) as client:
        raised = await client.call_tool(
            "raise_alert", {"run_id": "run-012", "reason": "mean_biomass z > 5"}
        )
        lifted = await client.call_tool("lift_quarantine", {})
        health = await client.call_tool("campaign_health", {})
        repeated = await client.call_tool(
            "raise_alert", {"run_id": "run-012", "reason": "mean_biomass z > 5"}
        )

    sentinel = tmp_path / "data" / "QUARANTINE"
    assert raised.data["quarantined"] is True
    assert raised.data["path"] == str(sentinel)
    assert lifted.data["lifted"] is True
    assert lifted.data["path"] == str(sentinel)
    assert lifted.data["acknowledged_run_id"] == "run-012"
    assert Path(lifted.data["acknowledgement_path"]).is_file()
    assert health.data["acknowledged_anomalous"] == ["run-012"]
    assert health.data["unresolved_anomalous"] == []
    assert repeated.data["quarantined"] is False
    assert repeated.data["acknowledged"] is True
    assert not sentinel.exists()


async def test_unsupported_semantics_fail_instead_of_falling_back(native_server) -> None:
    """A missing native capability is an explicit typed tool error."""
    async with Client(native_server) as client:
        with pytest.raises(ToolError, match="capability_unavailable"):
            await client.call_tool("get_model_card", {"model_id": "model-1"})


async def test_cross_domain_correlation_uses_same_native_evidence_once(native_server) -> None:
    """Correlation keeps the two domain labels even when one store serves both."""
    async with Client(native_server) as client:
        result = await client.call_tool("trace_correlation", {"correlation_id": "correlation-1"})

    assert result.data["agentic"]["count"] == 1
    assert result.data["artifact"]["count"] == 1
    assert result.data["agentic"]["items"] == result.data["artifact"]["items"]
