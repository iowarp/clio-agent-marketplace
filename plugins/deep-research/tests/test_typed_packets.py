"""Researchers hand the critic typed claims; a researcher without them still passes notes."""

from __future__ import annotations

from typing import Any

from test_deep_research_flow import Children, Planner, ScriptedCtx, audit, make_flow, of, run

CLAIM = {
    "text": "HDF5 2.0.0 was released in November 2025.",
    "kind": "FACT",
    "url": "https://www.hdfgroup.org/2025/11/release-of-hdf5-2-0-0/",
    "quote": "HDF5 2.0.0 now adheres to semantic versioning",
}


class TypedChildren(Children):
    def __call__(self, target: str, payload: Any) -> dict[str, Any]:
        if target == "researcher":
            return {
                "answer": "## Assignment\nnotes and the search log",
                "workflow_state": {"packet": {"claims": [CLAIM, {"kind": "FACT"}]}},
            }
        return super().__call__(target, payload)


def test_typed_claims_reach_the_critic_and_invalid_entries_are_counted() -> None:
    ctx = ScriptedCtx(TypedChildren([audit()]))
    run(make_flow(Planner(["a"])), ctx)
    (packet,) = of(ctx, "critic")[0]["input"]["packets"]
    # The researcher never fetched the page, so the claim reaches the critic unchecked.
    assert "claims" not in packet
    assert packet["unchecked"] == [
        {
            **CLAIM,
            "gate": "page_not_fetched",
            "reason": "the researcher did not successfully read the cited page",
        }
    ]
    assert packet["evidence"].startswith("## Assignment")
    assert {"event": "packet_claims_invalid", "direction": "d1", "dropped": 1} in ctx.events


def test_a_researcher_without_typed_claims_still_passes_its_notes() -> None:
    ctx = ScriptedCtx(Children([audit()]))
    run(make_flow(Planner(["a"])), ctx)
    (packet,) = of(ctx, "critic")[0]["input"]["packets"]
    assert "claims" not in packet and packet["evidence"] == "packet for a"
