"""Every tool on both MCP servers must declare a human-readable display
title (FastMCP's Tool.title / ToolAnnotations.title). clio-agent forwards
this onto the wire as tool_title (#1188) for the UI to render instead of the
raw snake_case tool name -- so a title-less tool would show up in the
transcript as a bare function name.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastmcp import Client

from spotter_ai.server import create_server as create_spotter_server
from spotter_ai.workload import create_server as create_workload_server


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "provenance.sqlite"


class TestEveryToolHasATitle:
    async def test_workload_server_tools(self, db_path: Path) -> None:
        server = create_workload_server(db_path)
        async with Client(server) as client:
            tools = await client.list_tools()

        assert {t.name for t in tools} == {"measure_cohort", "campaign_status", "lift_quarantine"}
        for tool in tools:
            assert tool.title, f"{tool.name} has no title"
            assert tool.title != tool.name, f"{tool.name}'s title is just its raw name"

    async def test_spotter_server_tools(self, db_path: Path) -> None:
        server = create_spotter_server(db_path)
        async with Client(server) as client:
            tools = await client.list_tools()

        assert {t.name for t in tools} == {
            "list_runs",
            "run_health",
            "campaign_health",
            "diff_runs",
            "trace_lineage",
            "read_artifact",
            "wait_for_new_runs",
            "raise_alert",
            "lift_quarantine",
        }
        for tool in tools:
            assert tool.title, f"{tool.name} has no title"
            assert tool.title != tool.name, f"{tool.name}'s title is just its raw name"

    async def test_titles_read_as_sentence_case_short_verbs(self, db_path: Path) -> None:
        """Titles must read as short human verbs, sentence case -- not
        jargon, not a restatement of the snake_case tool name.
        """
        workload_server = create_workload_server(db_path)
        spotter_server = create_spotter_server(db_path)

        async with Client(workload_server) as client:
            workload_titles = {t.name: t.title for t in await client.list_tools()}
        async with Client(spotter_server) as client:
            spotter_titles = {t.name: t.title for t in await client.list_tools()}

        expected = {
            "measure_cohort": "Measure plant cohort",
            "campaign_status": "Campaign status",
            "lift_quarantine": "Lift quarantine",
        }
        assert workload_titles == expected

        expected_spotter = {
            "list_runs": "List campaign runs",
            "run_health": "Run health check",
            "campaign_health": "Campaign health sweep",
            "diff_runs": "Compare two runs",
            "trace_lineage": "Trace run lineage",
            "read_artifact": "Read provenance artifact",
            "wait_for_new_runs": "Wait for new runs",
            "raise_alert": "Raise anomaly alert",
            "lift_quarantine": "Lift quarantine",
        }
        assert spotter_titles == expected_spotter
