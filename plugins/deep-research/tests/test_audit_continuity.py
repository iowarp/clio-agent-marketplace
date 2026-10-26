"""Invalid requirement identities must not erase independently bound evidence."""

import sys
from copy import deepcopy
from typing import Any

import pytest
from test_deep_research_flow import (
    Children,
    Planner,
    ScriptedCtx,
    audit,
    claim,
    flow_module,
    gap,
    make_flow,
    of,
    run,
    source_fixture,
)

from clio_agent.flows.outcomes import FlowStall

owner = sys.modules[flow_module.Audit.__module__]


def limit(question: str) -> dict[str, Any]:
    """A material requirement that cannot trigger another web round."""
    return gap(question, closure_kind="design_limit", required_tools=[])


def invalid_id(question: str) -> dict[str, Any]:
    """Keep semantics valid while supplying an incorrect derived ID."""
    return {**limit(question), "gap_id": "gap_invalid_model_id"}


def records() -> dict[str, Any]:
    """Use successful immutable source fixtures through the real binding parser."""
    return flow_module.source_records([source_fixture(1, "critic")], {"critic"})


def test_same_round_empty_repair_retains_bound_claims_rejections_and_all_requirements() -> None:
    rejected = {"claim": "unsupported assertion", "reason": "not documented", "source_url": ""}
    first = audit([claim(1), claim(2)], [rejected], [invalid_id("stack"), invalid_id("quota")])
    ctx = ScriptedCtx(Children([first, audit()]))
    result = run(make_flow(Planner(["sources"])), ctx)
    assert result["verified"] == [claim(1), claim(2)]
    assert result["rejected"] == [rejected]
    assert result["gaps_unresolved"] == [limit("stack"), limit("quota")]
    repair = of(ctx, "critic")[1]["input"]
    assert repair["validated_prior_ledger"]["verified"] == [claim(1), claim(2)]
    assert repair["open_requirements"] == [limit("stack"), limit("quota")]
    event = next(row for row in ctx.events if row["event"] == "critic_audit_continuity")
    assert event["retained_claim_ids"] == [claim(1)["claim_id"], claim(2)["claim_id"]]
    assert [row["raw"]["gap_id"] for row in event["gap_id_repairs"]] == [
        "gap_invalid_model_id",
        "gap_invalid_model_id",
    ]


def test_repaired_audit_that_repeats_invalid_id_is_still_rejected() -> None:
    bad = audit([claim(1)], gaps=[invalid_id("stack")])
    ctx = ScriptedCtx(Children([bad, bad]))
    with pytest.raises(FlowStall) as failure:
        run(make_flow(Planner(["sources"])), ctx)
    assert failure.value.stall == "critic_audit_invalid"
    assert len(of(ctx, "critic")) == 2


def test_repair_can_explicitly_withdraw_a_carried_proposition() -> None:
    rejection = {
        "claim": "claim 1",
        "reason": "reconsidered",
        "source_url": "https://example.org/1",
    }
    ctx = ScriptedCtx(
        Children(
            [
                audit([claim(1), claim(2)], gaps=[invalid_id("stack")]),
                audit(rejected=[rejection], gaps=[limit("stack")]),
            ]
        )
    )
    result = run(make_flow(Planner(["sources"])), ctx)
    assert result["verified"] == [claim(2)]
    assert result["rejected"] == [rejection]


@pytest.mark.parametrize("fault", ["schema", "quote", "url", "missing", "failed"])
def test_only_individually_typed_and_bound_neighbor_rows_are_carried(fault: str) -> None:
    bad = deepcopy(claim(1))
    available = records()
    if fault == "schema":
        bad["claim"] = ""
    elif fault == "quote":
        bad["evidence"][0]["quote"] = "unfetched passage"
    elif fault == "url":
        bad["evidence"][0]["source_url"] = "https://elsewhere.test"
    elif fault == "missing":
        bad["evidence"][0]["task_handle"] = "fetch_missing"
    else:
        failed = source_fixture(1, "critic")
        failed["task"]["status"] = "failed"
        available = flow_module.source_records([failed], {"critic"})
    # The valid neighbor uses a separate source, so one bad row cannot erase it.
    available.update(flow_module.source_records([source_fixture(2, "critic")], {"critic"}))
    ledger, diagnostic = owner.repair_context(
        {"verified": [bad, claim(2)], "rejected": [{"claim": "x"}]}, [], None, available
    )
    assert [row.model_dump() for row in ledger.verified] == [claim(2)]
    assert ledger.rejected == []
    assert {row["field"] for row in diagnostic["excluded_rows"]} == {"verified", "rejected"}


@pytest.mark.parametrize(
    "row",
    [
        None,
        {"question": "missing closure"},
        {"question": "bad action", "closure_kind": "workflow_action"},
    ],
)
def test_unrepresentable_requirement_stalls_instead_of_disappearing(row: Any) -> None:
    with pytest.raises(FlowStall) as failure:
        owner.repair_context({"gaps": [row]}, [], None, {})
    assert failure.value.stall == "critic_requirement_invalid"


def test_partial_ledger_does_not_share_mutable_claim_objects_with_earlier_audit() -> None:
    earlier = flow_module.Audit.model_validate({"verified": [claim(1)]})
    ledger, _ = owner.repair_context({}, [], earlier, records())
    ledger.verified[0].evidence[0].quote = "changed copy"
    assert earlier.verified[0].evidence[0].quote == "passage 1"


def test_valid_same_round_resolution_survives_unrelated_gap_id_repair() -> None:
    pending = [flow_module.Gap.model_validate(gap("answered question"))]
    resolution = {
        "gap_id": pending[0].gap_id,
        "basis": "new_evidence",
        "reason": "read source",
        "source_urls": ["https://example.org/1"],
        "receipt_ids": [],
    }
    ledger, diagnostics = owner.repair_context(
        {"verified": [claim(1)], "gaps": [invalid_id("stack")], "resolved_gaps": [resolution]},
        pending,
        None,
        records(),
    )
    assert [row.model_dump() for row in ledger.gaps] == [limit("stack")]
    assert diagnostics["retained_resolutions"] == [resolution]
    from clio_agent.flows.values import CallResult

    final, errors = owner._audit_of(
        CallResult(audit(), handle="repair", target="critic", kind="subagent"),
        [*pending, *ledger.gaps],
        ledger,
        carry_resolutions=True,
    )
    assert final is not None and not errors
    assert [row.model_dump() for row in final.resolved_gaps] == [resolution]
    assert [row.model_dump() for row in final.gaps] == [limit("stack")]
    # Explicitly reopening the old question overrides its carried closure.
    reopened, errors = owner._audit_of(
        CallResult(
            audit(gaps=[pending[0].model_dump()]), handle="repair", target="critic", kind="subagent"
        ),
        [*pending, *ledger.gaps],
        ledger,
        carry_resolutions=True,
    )
    assert reopened is not None and not errors and reopened.resolved_gaps == []
    assert pending[0].gap_id in {row.gap_id for row in reopened.gaps}


def test_resolution_without_bound_support_is_not_preserved() -> None:
    pending = [flow_module.Gap.model_validate(gap("unanswered question"))]
    ledger, diagnostic = owner.repair_context(
        {
            "resolved_gaps": [
                {
                    "gap_id": pending[0].gap_id,
                    "basis": "new_evidence",
                    "reason": "claimed",
                    "source_urls": ["https://unfetched.test"],
                }
            ]
        },
        pending,
        None,
        {},
    )
    assert ledger.resolved_gaps == [] and ledger.gaps == pending
    assert diagnostic["excluded_rows"][0]["field"] == "resolved_gaps"
