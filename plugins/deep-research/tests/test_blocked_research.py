"""A blocked research round stops the run with its reason instead of researching again."""

from __future__ import annotations

from typing import Any

import pytest
from test_deep_research_flow import (
    Children,
    Planner,
    ScriptedCtx,
    audit,
    claim,
    gap,
    make_flow,
    of,
    run,
)

from clio_agent.flows.outcomes import FlowStall

REFUSED = {
    "receipt_id": "refused-1",
    "tool_name": "web_search",
    "decision_status": "auto_denied",
    "action": "",
    "reason": "policy_deny",
}


class RefusingCtx(ScriptedCtx):
    """Every search from ``refuse_from`` researchers on is refused by a policy."""

    def __init__(self, *args: Any, refuse_from: int = 1, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.refuse_from = refuse_from
        self.observed = 0

    async def permission_receipts(self, *, refresh: bool = False) -> dict[str, Any]:
        researched = len(of(self, "researcher"))
        refused = researched >= self.refuse_from
        rows = [{**REFUSED, "receipt_id": f"refused-{researched}"}] if refused else []
        return {"status": "available", "receipts": rows}

    # A refused call never ran, so a researcher leaves no tool result; the base
    # context returns none for researchers and the critic's fetches as before.


def _declined(handle: str) -> dict[str, Any]:
    body = {"ok": False, "error": {"code": "search_not_approved"}}
    return {
        "task": {"kind": "MCP", "status": "completed", "tool": "search",
                 "backend": {"server": "web"}, "owner": {"assignment_id": handle}},
        "value": {"structuredContent": body},
    }  # fmt: skip


def test_a_round_one_with_every_search_refused_stops_with_the_reason() -> None:
    ctx = RefusingCtx(Children([audit()]))
    with pytest.raises(FlowStall) as stalled:
        run(make_flow(Planner(["a", "b"])), ctx)
    assert stalled.value.stall == "research_blocked"
    assert "web_search" in str(stalled.value) and "policy_deny" in str(stalled.value)
    assert of(ctx, "critic") == []  # nothing to verify, no gap rounds
    assert [e["event"] for e in ctx.events if e.get("event") == "research_blocked"] == [
        "research_blocked"
    ]


def test_every_source_declined_stops_with_the_way_back() -> None:
    class DeclinedCtx(ScriptedCtx):
        async def tool_results(self, handle: str) -> list[dict[str, Any]]:
            return [_declined(handle)]

    ctx = DeclinedCtx(Children([audit()]))
    with pytest.raises(FlowStall) as stalled:
        run(make_flow(Planner(["a"])), ctx)
    assert stalled.value.stall == "research_blocked"
    assert "Settings > Web search" in str(stalled.value)


def test_a_blocked_gap_round_ends_the_rounds_and_delivers_what_was_verified() -> None:
    first = audit([claim(1)], gaps=[gap("open question")])
    ctx = RefusingCtx(Children([first, audit()]), refuse_from=2)
    result = run(make_flow(Planner(["a"]), max_rounds=2), ctx)
    assert [r["key"] for r in of(ctx, "researcher")] == ["research:d1", "research:g2.1"]
    # The blocked round is never audited: every critic call is about round 1.
    assert {c["input"].get("round", 1) for c in of(ctx, "critic")} == {1}
    assert result["verified"] == [claim(1)]
    assert any(e.get("event") == "research_blocked" and e["round"] == 2 for e in ctx.events)


def test_a_permission_gap_stops_further_rounds() -> None:
    needs = gap(
        "May this workspace search?",
        closure_kind="external_input",
        required_tools=["web_search"],
        input_kind="permission",
        permission_requirement={"scope": "workspace", "scope_id": "ws_a"},
    )
    ctx = ScriptedCtx(Children([audit([claim(1)], gaps=[needs, gap("more to research")])]))
    run(make_flow(Planner(["a"]), max_rounds=2), ctx)
    assert [r["key"] for r in of(ctx, "researcher")] == ["research:d1"]
    assert {"event": "gap_rounds_stopped", "reason": "permission"} in ctx.events
