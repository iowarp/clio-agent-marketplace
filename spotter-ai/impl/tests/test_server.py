"""FastMCP contract tests for the provider-aware Spotter surface."""

import json
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

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
    return create_server(service=ProvenanceService(provider, provider))


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
    }
    for tool in tools:
        assert "provider" not in tool.inputSchema.get("properties", {})
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.idempotentHint is True
        assert tool.annotations.openWorldHint is True


async def test_capabilities_name_the_active_providers(native_server) -> None:
    """Capability discovery reports both independent provider domains."""
    async with Client(native_server) as client:
        result = await client.call_tool("capabilities", {})

    assert result.data["agentic"]["provider"] == "native"
    assert result.data["artifact"]["provider"] == "native"
    assert "get_timeline" in result.data["agentic"]["capabilities"]
    assert "list_pipelines" not in result.data["artifact"]["capabilities"]


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
