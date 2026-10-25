"""Parent report stages settle from their own exact-document receipts."""

import hashlib
import sys
from pathlib import Path
from typing import Any

import pytest
from test_deep_research_flow import (
    Children,
    Planner,
    ScriptedCtx,
    Writer,
    audit,
    claim,
    flow_module,
    gap,
    make_flow,
    of,
    run,
)

from clio_agent.flows.outcomes import CallFailed

report = sys.modules[flow_module.ReportSynthesis.__module__]


def action_gap(action: str) -> dict[str, Any]:
    """Build a separately identifiable parent-stage requirement."""
    return gap(action, closure_kind="workflow_action", required_tools=[], action=action)


def test_review_is_advertised_and_settled_without_delegating_to_web(tmp_path: Path) -> None:
    requirements = [action_gap("review_report"), action_gap("persist_report")]
    ctx = ScriptedCtx(Children([audit([claim(1)], gaps=requirements)]), workspace=tmp_path)
    writer = Writer()
    result = run(make_flow(Planner([*requirements, "source question"]), writer), ctx)
    assert len(of(ctx, "researcher")) == 1
    actions = of(ctx, "critic")[0]["input"]["capabilities"]["workflow_actions"]
    assert actions["review_report"]["stage"] == "after_draft"
    assert actions["review_report"]["available"] is True
    assert writer.given[0]["unresolved_gaps"] == []
    assert result["delivery_requirements"] == requirements
    assert result["gaps_unresolved"] == []
    receipts = result["action_receipts"]
    assert receipts["review_report"]["status"] == "accepted_by_reviewer"
    assert receipts["review_report"]["verification"] == "model_judgment_of_exact_draft"
    assert receipts["review_report"]["report_sha256"] == result["persistence"]["text_sha256"]


def test_failed_save_keeps_review_closed_and_unknown_action_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    requirements = [action_gap(name) for name in ("review_report", "persist_report", "publish")]
    monkeypatch.setattr(
        flow_module,
        "_persist_report",
        lambda *args: {"status": "failed", "path": "", "reason": "readback_mismatch"},
    )
    ctx = ScriptedCtx(Children([audit([claim(1)], gaps=requirements)]), workspace=tmp_path)
    result = run(make_flow(Planner(["source question"])), ctx)
    assert result["persistence"]["status"] == "failed"
    assert result["action_receipts"]["review_report"]["status"] == "accepted_by_reviewer"
    assert result["gaps_unresolved"] == [requirements[2], requirements[1]]


@pytest.mark.parametrize(
    "reviews",
    [
        [],
        [{"status": "issues_found", "report_sha256": "x"}],
        [{"status": "accepted_by_reviewer", "report_sha256": "x"}],
    ],
)
def test_review_without_matching_acceptance_does_not_close(reviews: list[dict[str, Any]]) -> None:
    receipts = report.action_receipts("actual document", reviews, {"status": "unavailable"})
    assert not report.action_completed(action_gap("review_report"), receipts)
    assert not report.action_completed(action_gap("persist_report"), receipts)
    assert not report.action_completed(action_gap("publish"), receipts)


def test_successful_save_receipt_for_a_different_document_does_not_close() -> None:
    digest = hashlib.sha256(b"different document").hexdigest()
    receipts = report.action_receipts(
        "actual document",
        [],
        {"status": "verified", "text_sha256": digest, "readback_text_sha256": digest},
    )
    assert not report.action_completed(action_gap("persist_report"), receipts)


def test_invalid_gap_identity_is_recorded_before_repair_admission_failure() -> None:
    invalid = action_gap("review_report")
    invalid["gap_id"] = "gap_not_the_requirement_hash"

    def children(target: str, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("repair"):
            raise CallFailed("repair admission failed", handle="task_failed")
        return Children([audit([claim(1)], gaps=[invalid])])(target, payload)

    ctx = ScriptedCtx(children)
    with pytest.raises(CallFailed, match="repair admission failed"):
        run(make_flow(Planner(["source question"])), ctx)
    event = next(row for row in ctx.events if row["event"] == "critic_audit_repair")
    assert event["critic"] == "task_2"
    assert any("gap_id does not identify" in problem for problem in event["problems"])
