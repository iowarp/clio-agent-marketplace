"""The delegation reminder reaches the agent when it loads run_flow, and only then."""

from __future__ import annotations

from pathlib import Path

from clio_agent.injections.declarations import read_dir
from clio_agent.injections.template import render_text

FOLDER = Path(__file__).resolve().parents[1] / "ai.iowarp.clio" / "injections"


def _render(query: str, is_error: bool = False) -> str:
    (reminder,) = [r for r in read_dir(FOLDER, plugin="deep-research") if "delegate" in r.name]
    assert reminder.event == "tool_result" and reminder.tool == "search_tools"
    tool = {"name": "search_tools", "args": {"query": query}, "is_error": is_error, "chars": 10}
    return render_text(reminder.text, {"tool": tool}, reminder.name)


def test_loading_run_flow_brings_the_reminder() -> None:
    text = _render("select:run_flow,get_task_result")
    assert "researcher_model" in text and "list_models" in text


def test_other_loads_and_failed_loads_bring_nothing() -> None:
    assert _render("select:web_search") == ""
    assert _render("select:run_flow", is_error=True) == ""
