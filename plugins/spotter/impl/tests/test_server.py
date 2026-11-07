"""FastMCP contract tests for the provider-aware Spotter surface."""

import json
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from spotter_ai.config import NativeQueryConfig, SpotterConfig
from spotter_ai.errors import ProvenanceError
from spotter_ai.providers.jsonl import JsonlProvider
from spotter_ai.server import WATCHER_TOOLS, create_server
from spotter_ai.service import ProvenanceService


def _native_provider(tmp_path: Path) -> JsonlProvider:
    """One real native provider over a single correlated model-call event."""
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
    return JsonlProvider(NativeQueryConfig(journal, tmp_path))


@pytest.fixture
def native_server(tmp_path: Path):
    """Create a server backed by one real native provider."""
    provider = _native_provider(tmp_path)
    return create_server(service=ProvenanceService(provider, provider))


async def test_exposes_purpose_specific_tools_without_provider_arguments(native_server) -> None:
    """The watcher is offered only its provenance tools; configuration selects providers."""
    async with Client(native_server) as client:
        tools = await client.list_tools()

    assert {tool.name for tool in tools} == WATCHER_TOOLS
    for tool in tools:
        assert "provider" not in tool.inputSchema.get("properties", {})
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.idempotentHint is True


def test_capabilities_name_the_active_providers(tmp_path: Path) -> None:
    """Capability discovery reports both independent provider domains."""
    provider = _native_provider(tmp_path)
    described = ProvenanceService(provider, provider).capabilities()

    assert described["agentic"]["provider"] == "native"
    assert described["artifact"]["provider"] == "native"
    assert "get_timeline" in described["agentic"]["capabilities"]
    assert "list_pipelines" not in described["artifact"]["capabilities"]
    assert "campaign_forensics" not in described


async def test_unsupported_artifact_semantics_are_not_served(native_server, tmp_path: Path) -> None:
    """A lineage operation the artifact provider cannot answer is off the menu, not faked."""
    async with Client(native_server) as client:
        names = {tool.name for tool in await client.list_tools()}
        with pytest.raises(ToolError):
            await client.call_tool("get_model_card", {"model_id": "model-1"})

    provider = _native_provider(tmp_path)
    assert "get_model_card" not in names
    assert (
        "get_model_card"
        not in ProvenanceService(provider, provider).capabilities()["artifact"]["capabilities"]
    )


async def test_artifact_tools_follow_the_artifact_providers_operations(tmp_path: Path) -> None:
    """Recorded correlation evidence serves the trace; no artifact lane serves none."""
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
    assert {"list_pipelines", "get_model_card", "trace_correlation"} <= provider.capabilities()
    async with Client(create_server(service=ProvenanceService(provider, provider))) as client:
        served = {tool.name for tool in await client.list_tools()}
    assert served == WATCHER_TOOLS

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
    assert served == {"query_tasks"}


async def test_cross_domain_correlation_uses_same_native_evidence_once(native_server) -> None:
    """Correlation keeps the two domain labels even when one store serves both."""
    async with Client(native_server) as client:
        result = await client.call_tool("trace_correlation", {"correlation_id": "correlation-1"})

    assert result.data["agentic"]["count"] == 1
    assert result.data["artifact"]["count"] == 1
    assert result.data["agentic"]["items"] == result.data["artifact"]["items"]


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

    assert tasks.data["count"] == 0
    assert tasks.data["lane"]["domain"] == "agentic"
    assert tasks.data["lane"]["provider"] == "native"
    assert tasks.data["lane"]["selected_by"] == "default_jsonl"
    assert tasks.data["lane"]["hint"].startswith("lane_defaulted: flowcept is enabled")


async def test_a_configured_lane_gives_no_defaulted_hint(native_server) -> None:
    """Results from the configured lane carry the lane without a hint."""
    async with Client(native_server) as client:
        result = await client.call_tool("query_tasks", {"limit": 1})

    assert result.data["lane"]["provider"] == "native"
    assert "hint" not in result.data["lane"]


async def test_an_unreadable_store_keeps_its_tools_and_reports_its_error(tmp_path: Path) -> None:
    """Startup never hides the correlation trace when the store cannot list its operations."""
    journal = tmp_path / "events.jsonl"
    journal.write_text(json.dumps({"record_type": "pipeline"}) + "\n", encoding="utf-8")
    provider = JsonlProvider(NativeQueryConfig(journal, tmp_path))
    service = ProvenanceService(provider, provider)
    async with Client(create_server(service=service)) as client:
        served = {tool.name for tool in await client.list_tools()}
        with pytest.raises(ToolError, match="invalid_query"):
            await client.call_tool("trace_correlation", {"correlation_id": "c-1"})
    with pytest.raises(ProvenanceError) as unreadable:
        service.require_artifact("list_artifacts").list_artifacts(limit=10)
    assert unreadable.value.code == "invalid_query"
    assert served == WATCHER_TOOLS
