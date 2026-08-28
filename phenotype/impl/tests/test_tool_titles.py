"""Every workload MCP tool must declare a human-readable display title
(FastMCP's Tool.title / ToolAnnotations.title). clio-agent forwards this onto
the wire as tool_title (#1188) for the UI to render instead of the raw
snake_case tool name -- so a title-less tool would show up in the transcript
as a bare function name.

(The SPOTTER forensic server's title coverage lives with that server in the
``spotter-ai`` pack -- the two packs are separate projects by design.)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastmcp import Client

from phenotype_workload.workload import create_server as create_workload_server


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

    async def test_titles_read_as_sentence_case_short_verbs(self, db_path: Path) -> None:
        """Titles must read as short human verbs, sentence case -- not
        jargon, not a restatement of the snake_case tool name.
        """
        server = create_workload_server(db_path)
        async with Client(server) as client:
            titles = {t.name: t.title for t in await client.list_tools()}

        assert titles == {
            "measure_cohort": "Measure plant cohort",
            "campaign_status": "Campaign status",
            "lift_quarantine": "Lift quarantine",
        }
