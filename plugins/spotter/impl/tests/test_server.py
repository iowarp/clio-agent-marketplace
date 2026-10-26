"""FastMCP contract tests for the provider-aware Spotter surface."""

import json
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from spotter_ai.config import NativeQueryConfig, SpotterConfig
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
    return create_server(service=ProvenanceService(provider, provider))


async def test_exposes_purpose_specific_tools_without_provider_arguments(native_server) -> None:
    """The agent selects a question, while configuration selects providers."""
    async with Client(native_server) as client:
        tools = await client.list_tools()

    names = {tool.name for tool in tools}
    assert names == {
        "capabilities",
        "list_attention_calls",
        "inspect_attention",
        "list_campaigns",
        "list_workflows",
        "list_agents",
        "query_tasks",
        "summarize_tasks",
        "get_timeline",
        "list_executions",
        "list_artifact_types",
        "list_artifacts",
        "get_execution_lineage",
        "get_artifact_lineage",
        "trace_correlation",
    }
    for tool in tools:
        assert "provider" not in tool.inputSchema.get("properties", {})
        assert tool.annotations is not None
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
    assert "campaign_forensics" not in result.data


async def test_unsupported_artifact_semantics_are_not_served(native_server) -> None:
    """A lineage operation the artifact provider cannot answer is off the menu, not faked."""
    async with Client(native_server) as client:
        names = {tool.name for tool in await client.list_tools()}
        capabilities = await client.call_tool("capabilities", {})
        with pytest.raises(ToolError):
            await client.call_tool("get_model_card", {"model_id": "model-1"})

    assert "get_model_card" not in names
    assert "get_model_card" not in capabilities.data["artifact"]["capabilities"]


async def test_artifact_tools_follow_the_artifact_providers_operations(tmp_path: Path) -> None:
    """Recorded pipeline/model-card evidence serves those tools; no artifact lane serves none."""
    journal = tmp_path / "events.jsonl"
    journal.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {"schema_version": "spotter.provenance.v1", "record_type": "pipeline"},
                {"schema_version": "spotter.provenance.v1", "record_type": "model_card"},
            )
        )
        + "\n",
        encoding="utf-8",
    )
    provider = JsonlProvider(NativeQueryConfig(journal, tmp_path))
    async with Client(create_server(service=ProvenanceService(provider, provider))) as client:
        served = {tool.name for tool in await client.list_tools()}
    assert {"list_pipelines", "get_model_card", "trace_correlation"} <= served

    class NoArtifacts:
        name = "none"

        def capabilities(self) -> set[str]:
            return set()

        def health(self) -> dict[str, str]:
            return {"provider": self.name, "status": "ready"}

        def close(self) -> None:
            return None

    service = ProvenanceService(provider, NoArtifacts())  # type: ignore[arg-type]
    async with Client(create_server(service=service)) as client:
        served = {tool.name for tool in await client.list_tools()}
    artifact_tools = {
        "list_pipelines",
        "list_executions",
        "list_artifact_types",
        "list_artifacts",
        "get_execution_lineage",
        "get_artifact_lineage",
        "get_model_card",
        "trace_correlation",
    }
    assert not served & artifact_tools
    assert {"capabilities", "query_tasks", "get_timeline"} <= served


async def test_cross_domain_correlation_uses_same_native_evidence_once(native_server) -> None:
    """Correlation keeps the two domain labels even when one store serves both."""
    async with Client(native_server) as client:
        result = await client.call_tool("trace_correlation", {"correlation_id": "correlation-1"})

    assert result.data["agentic"]["count"] == 1
    assert result.data["artifact"]["count"] == 1
    assert result.data["agentic"]["items"] == result.data["artifact"]["items"]


async def test_capabilities_say_how_the_query_lane_was_chosen(tmp_path: Path) -> None:
    """A defaulted native lane names the enabled provider it does not query."""
    journal = tmp_path / "events.jsonl"
    journal.write_text("", encoding="utf-8")
    provider = JsonlProvider(NativeQueryConfig(journal, tmp_path))
    config = SpotterConfig(
        source_path=tmp_path / "clio.yaml",
        agentic_provider="jsonl",
        artifact_provider="native",
        agentic_selected_by="default_jsonl",
        agentic_alternatives=("flowcept",),
    )
    server = create_server(config, service=ProvenanceService(provider, provider))
    async with Client(server) as client:
        result = await client.call_tool("capabilities", {})

    assert result.data["agentic"]["selected_by"] == "default_jsonl"
    assert result.data["agentic"]["enabled_not_queried"] == ["flowcept"]


async def test_every_query_result_names_its_lane(tmp_path: Path) -> None:
    """A defaulted native lane that finds nothing says which enabled provider it skipped."""
    journal = tmp_path / "events.jsonl"
    journal.write_text("", encoding="utf-8")
    provider = JsonlProvider(NativeQueryConfig(journal, tmp_path))
    config = SpotterConfig(
        source_path=tmp_path / "clio.yaml",
        agentic_provider="jsonl",
        artifact_provider="native",
        agentic_selected_by="default_jsonl",
        agentic_alternatives=("flowcept",),
    )
    server = create_server(config, service=ProvenanceService(provider, provider))
    async with Client(server) as client:
        tasks = await client.call_tool("query_tasks", {})
        artifacts = await client.call_tool("list_artifacts", {})

    assert tasks.data["count"] == 0
    assert tasks.data["lane"]["domain"] == "agentic"
    assert tasks.data["lane"]["provider"] == "native"
    assert tasks.data["lane"]["selected_by"] == "default_jsonl"
    assert tasks.data["lane"]["hint"].startswith("lane_defaulted: flowcept is enabled")
    assert artifacts.data["lane"] == {"domain": "artifact", "provider": "native"}


async def test_a_configured_lane_gives_no_defaulted_hint(native_server) -> None:
    """Results from the configured lane carry the lane without a hint."""
    async with Client(native_server) as client:
        result = await client.call_tool("query_tasks", {"limit": 1})

    assert result.data["lane"]["provider"] == "native"
    assert "hint" not in result.data["lane"]


async def test_an_unreadable_store_keeps_its_tools_and_reports_its_error(tmp_path: Path) -> None:
    """Startup never hides the lineage tools when the store cannot list its operations."""
    journal = tmp_path / "events.jsonl"
    journal.write_text(json.dumps({"record_type": "pipeline"}) + "\n", encoding="utf-8")
    provider = JsonlProvider(NativeQueryConfig(journal, tmp_path))
    async with Client(create_server(service=ProvenanceService(provider, provider))) as client:
        served = {tool.name for tool in await client.list_tools()}
        with pytest.raises(ToolError, match="invalid_query"):
            await client.call_tool("list_artifacts", {})
    assert {"list_pipelines", "get_model_card", "trace_correlation"} <= served
