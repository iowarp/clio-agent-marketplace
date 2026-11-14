"""The deep-research flow on a scripted ``ctx``: method shape, bounds, typed audit, replay.

The ``ctx`` here implements the surface the flow uses (``call``, ``gather``, ``step``,
``record_event``) the way CLIO's runtime does: a call's identity is fixed when it is
made, a gather runs at most ``limit`` calls at once and hands back typed outcomes with
``return_exceptions``, and a step returns its recorded result on replay. Results are
``clio_agent.flows.values.CallResult`` objects, as the runtime returns them.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import dspy
import pytest

from clio_agent.flows.outcomes import CallFailed, FlowOutcome, FlowStall, GatherFailed
from clio_agent.flows.values import CallResult, FlowWorkspace
from clio_agent.plugins.loader import import_plugin_module
from clio_agent.sdk.flow import FlowOptionsInvalid

PLUGIN = Path(__file__).resolve().parents[1]
FLOW_FILE = PLUGIN / "ai.iowarp.clio" / "flows" / "deep_research.py"
PROMPT = PLUGIN / "ai.iowarp.clio" / "prompt"


def _load_flow_module() -> Any:
    return import_plugin_module(PLUGIN, "flows/deep_research.py")


flow_module = _load_flow_module()
DeepResearch = flow_module.DeepResearch


# --------------------------------------------------------------------------- ctx
class _Call:
    def __init__(self, ctx: ScriptedCtx, row: dict[str, Any]) -> None:
        self.ctx = ctx
        self.row = row

    def __await__(self) -> Any:
        return self.ctx._run(self.row).__await__()


class ScriptedCtx:
    """A flow ``ctx`` whose children are scripted and whose journal is a dict."""

    def __init__(
        self,
        script: Callable[[str, Any], dict[str, Any]],
        *,
        journal: dict[str, Any] | None = None,
        workspace: Path | None = None,
    ) -> None:
        self.script = script
        self.run_id = "flowrun_0123456789abcdef"
        self.workspace = FlowWorkspace(workspace)
        self.resolution = SimpleNamespace(
            subagents=[{"id": "researcher", "tools": ["web_search", "web_fetch"]}]
        )
        self.journal = journal if journal is not None else {"steps": {}, "calls": {}}
        self.calls: list[dict[str, Any]] = []
        self.steps: list[str] = []
        self.events: list[dict[str, Any]] = []
        self.in_flight = 0
        self.most_in_flight = 0

    def call(
        self,
        target: str,
        input: Any = None,
        *,
        evidence: Any = None,
        key: str = "",
        model: str = "",
        label: str = "",
    ) -> _Call:  # noqa: A002 - ctx.call's public parameter name
        row = {
            "target": target,
            "input": json.loads(json.dumps(input)),
            "evidence": list(evidence or []),
            "key": key,
            "model": model,
            "label": label,
        }
        self.calls.append(row)
        return _Call(self, row)

    async def _run(self, row: dict[str, Any]) -> CallResult:
        self.in_flight += 1
        self.most_in_flight = max(self.most_in_flight, self.in_flight)
        try:
            await asyncio.sleep(0)
            recorded = self.journal["calls"].get(row["key"])
            if recorded is None:
                handle = f"task_{len(self.journal['calls']) + 1}"
                try:
                    value = self.script(row["target"], row["input"])
                except FlowOutcome as outcome:
                    recorded = {"handle": handle, "outcome": outcome}
                else:
                    recorded = {"handle": handle, "value": value}
                self.journal["calls"][row["key"]] = recorded
            if "outcome" in recorded:
                raise recorded["outcome"]
            return CallResult(
                recorded["value"],
                handle=recorded["handle"],
                target=row["target"],
                kind="subagent",
                model=row["model"] or "acct/default",
            )
        finally:
            self.in_flight -= 1

    async def gather(
        self, calls: list[_Call], *, limit: int | None = None, return_exceptions: bool = False
    ) -> list[Any]:
        gate = asyncio.Semaphore(limit if limit and limit > 0 else max(1, len(calls)))

        async def bounded(call: _Call) -> Any:
            async with gate:
                try:
                    return await call
                except FlowOutcome as outcome:
                    return outcome

        results = list(await asyncio.gather(*(bounded(c) for c in calls)))
        if not return_exceptions and any(isinstance(r, FlowOutcome) for r in results):
            raise GatherFailed("a gathered call failed", results)
        return results

    async def step(self, fn: Callable[..., Any], *args: Any) -> Any:
        name = f"{fn.__qualname__}:{json.dumps(args, sort_keys=True)}"
        self.steps.append(fn.__qualname__)
        if name not in self.journal["steps"]:
            self.journal["steps"][name] = json.loads(json.dumps(fn(*args)))
        return self.journal["steps"][name]

    async def record_event(self, event: dict[str, Any]) -> None:
        self.events.append(event)

    async def permission_receipts(self, *, refresh: bool = False) -> dict[str, Any]:
        return {"status": "available", "receipts": []}

    async def tool_results(self, handle: str) -> list[dict[str, Any]]:
        owners = {}
        for row in self.journal["calls"].values():
            for verified in (
                row.get("value", {}).get("workflow_state", {}).get("audit", {}).get("verified", [])
            ):
                for edge in verified.get("evidence", []):
                    owners.setdefault(edge["task_handle"], row["handle"])
        return [
            source_fixture(int(match[1]), handle)
            for task, owner in owners.items()
            if owner == handle and (match := re.fullmatch(r"fetch_(\d+)", task))
        ]


# ----------------------------------------------------------------- the models
class Planner:
    """Stands in for the planner module: returns the directions it is given."""

    def __init__(self, questions: list[str | dict[str, Any]]) -> None:
        self.questions = questions
        self.asked: list[dict[str, Any]] = []

    def __call__(
        self,
        *,
        question: str,
        max_directions: int,
        capabilities: dict[str, Any],
        operational_evidence: dict[str, Any],
    ) -> Any:
        self.asked.append(
            {
                "question": question,
                "max_directions": max_directions,
                "capabilities": capabilities,
                "operational_evidence": operational_evidence,
            }
        )
        return dspy.Prediction(
            directions=[
                flow_module.Direction.model_validate(q if isinstance(q, dict) else gap(q))
                for q in self.questions
            ]
        )


class Coordinator:
    """Stands in for the coordinator.

    Scripted with ``decisions`` (one per round), it returns them in order. Otherwise
    it follows up every proposed web gap no assignment has asked yet while rounds
    remain, and lists them as open questions when none do.
    """

    def __init__(self, decisions: list[dict[str, Any]] | None = None) -> None:
        self.decisions = None if decisions is None else list(decisions)
        self.given: list[dict[str, Any]] = []

    def __call__(
        self,
        *,
        question: str,
        plan: list[dict[str, Any]],
        assignments: list[dict[str, Any]],
        verified: list[dict[str, Any]],
        proposed_gaps: list[Any],
        researcher_tools: list[str],
        rounds_left: int,
        max_follow_ups: int | None,
    ) -> Any:
        self.given.append(
            {
                "question": question,
                "plan": plan,
                "assignments": assignments,
                "verified": verified,
                "proposed_gaps": [row.model_dump() for row in proposed_gaps],
                "researcher_tools": researcher_tools,
                "rounds_left": rounds_left,
                "max_follow_ups": max_follow_ups,
            }
        )
        if self.decisions is not None:
            decision = self.decisions.pop(0) if self.decisions else {}
            return dspy.Prediction(
                across=decision.get("across", []),
                follow_ups=decision.get("follow_ups", []),
                open_questions=decision.get("open_questions", []),
            )
        asked = {row["question"] for row in assignments}
        rows = [
            {k: v for k, v in row.model_dump().items() if k != "gap_id"}
            for row in proposed_gaps
            if row.closure_kind == "web_research" and row.question not in asked
        ]
        if rounds_left:
            return dspy.Prediction(across=[], follow_ups=rows, open_questions=[])
        return dspy.Prediction(across=[], follow_ups=[], open_questions=rows)


class Writer:
    """Stands in for the writer module: cites every verified claim it was given."""

    def __init__(self, extra: str = "", repairable: bool = False) -> None:
        self.extra = extra
        self.repairable = repairable
        self.given: list[dict[str, Any]] = []

    def __call__(
        self,
        *,
        question: str,
        verified: list[Any],
        across: list[Any],
        unresolved_gaps: list[Any],
        delivery: dict[str, Any],
        operational_evidence: dict[str, Any],
        citation_problems: list[str],
        review_feedback: list[Any],
        previous_blocks: list[Any],
    ) -> Any:
        self.given.append(
            {
                "question": question,
                "verified": [c.model_dump() for c in verified],
                "across": across,
                "unresolved_gaps": [g.model_dump() for g in unresolved_gaps],
                "delivery": delivery,
                "operational_evidence": operational_evidence,
                "citation_problems": citation_problems,
                "review_feedback": [row.model_dump() for row in review_feedback],
            }
        )
        blocks = [{"text": "# Report", "kind": "structure", "claim_ids": []}]
        blocks += [
            {"text": c.claim, "kind": "source_fact", "claim_ids": [c.claim_id]} for c in verified
        ]
        extra = "" if self.repairable and (citation_problems or review_feedback) else self.extra
        if extra:
            blocks.append({"text": extra, "kind": "proposal", "claim_ids": []})
        return dspy.Prediction(blocks=blocks)


def source_fixture(n: int, auditor: str) -> dict[str, Any]:
    reference = {
        "session_id": "source-fixture",
        "scope": "test",
        "content_id": f"result_{n}",
        "sha256": hashlib.sha256(f"result {n}".encode()).hexdigest(),
    }
    return {
        "task": {
            "handle": f"fetch_{n}",
            "kind": "MCP",
            "status": "completed",
            "tool": "fetch",
            "backend": {"server": "web"},
            "owner": {"assignment_id": auditor},
            "terminal_at": "2026-01-01T00:00:00Z",
        },
        "result_reference": reference,
        "value": {
            "ok": True,
            "status": 200,
            "content": f"passage {n}",
            "url": f"https://example.org/{n}",
            "title": f"Source {n}",
        },
    }


def claim(n: int) -> dict[str, Any]:
    record = source_fixture(n, "critic")
    url = f"https://example.org/{n}"
    body_hash = hashlib.sha256(f"passage {n}".encode()).hexdigest()
    source_id = (
        "source_"
        + hashlib.sha256(
            json.dumps([record["result_reference"], url, body_hash], sort_keys=True).encode()
        ).hexdigest()[:24]
    )
    return flow_module.VerifiedClaim.model_validate(
        {
            "claim": f"claim {n}",
            "evidence": [
                {
                    "task_handle": f"fetch_{n}",
                    "source_url": url,
                    "quote": f"passage {n}",
                    "source_title": f"Source {n}",
                    "supports": f"claim {n}",
                    "source_id": source_id,
                }
            ],
        }
    ).model_dump()


class Reviewer:
    """Script only the semantic judgment; production still binds actual source fixtures."""

    def __init__(self, issues: list[list[dict[str, Any]]] | None = None) -> None:
        self.issues = list(issues or [])
        self.given: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> Any:
        self.given.append(kwargs)
        return dspy.Prediction(issues=self.issues.pop(0) if self.issues else [])


def gap(text: str, **closure: Any) -> dict[str, Any]:
    return flow_module.Gap.model_validate(
        {
            "question": text,
            "why": "it could change the answer",
            "answer_looks_like": "a filing",
            "closure_kind": "web_research",
            "required_tools": ["web_fetch"],
            "action": "",
            **closure,
        }
    ).model_dump()


def audit(
    verified: list[Any] = (),
    rejected: list[Any] = (),
    gaps: list[Any] = (),
    resolved: list[str] = (),
) -> dict:
    return {
        "answer": "audit summary",
        "workflow_state": {
            "audit": {
                "verified": list(verified),
                "rejected": list(rejected),
                "gaps": list(gaps),
                "resolved_gaps": [
                    {
                        "gap_id": gap(q)["gap_id"],
                        "basis": "new_evidence",
                        "reason": "The verified passage answers it",
                        "source_urls": [claim(1)["evidence"][0]["source_url"]],
                    }
                    for q in resolved
                ],
            }
        },
    }


class Children:
    """Scripted researcher and critic: researchers echo their direction; critics pop audits."""

    def __init__(self, audits: list[dict[str, Any]], fail: set[str] | None = None) -> None:
        self.audits = list(audits)
        self.fail = fail or set()

    def __call__(self, target: str, payload: Any) -> dict[str, Any]:
        if target == "researcher":
            question = payload["direction"]["question"]
            if question in self.fail:
                raise CallFailed(f"researcher on {question!r} failed", handle="task_failed")
            return {"answer": f"packet for {question}"}
        if target == "critic":
            return self.audits.pop(0) if self.audits else audit()
        raise AssertionError(f"unexpected target {target}")


def make_flow(
    planner: Planner,
    writer: Writer | None = None,
    reviewer: Reviewer | None = None,
    coordinator: Coordinator | None = None,
    **options: Any,
) -> Any:
    flow = DeepResearch()
    for key, value in DeepResearch.checked_options(options).items():
        setattr(flow, key, value)
    flow.planner = planner
    flow.coordinator = coordinator or Coordinator()
    flow.writer = writer or Writer()
    flow.reviewer = reviewer or Reviewer()
    return flow


def run(flow: Any, ctx: ScriptedCtx, question: str = "What changed?") -> dict[str, Any]:
    return asyncio.run(flow.forward(question, ctx))


def of(ctx: ScriptedCtx, target: str) -> list[dict[str, Any]]:
    return [row for row in ctx.calls if row["target"] == target]


# --------------------------------------------------------------------- tests
def test_the_critic_receives_public_evidence_before_the_final_addendum() -> None:
    packet = "A substantive finding, primary source and limitation.\n" * 350
    addendum = "The last source finished."

    def children(target: str, payload: Any) -> dict[str, Any]:
        if target == "researcher":
            return {
                "answer": addendum,
                "response_parts": [
                    {"id": "packet", "type": "text", "text": packet},
                    {"id": "addendum", "type": "text", "text": addendum},
                ],
            }
        assert target == "critic"
        assert payload["packets"][0]["evidence"] == packet + "\n\n" + addendum
        return audit([claim(1)])

    ctx = ScriptedCtx(children)
    result = run(make_flow(Planner(["a"])), ctx)
    assert result["verified"] == [claim(1)]


def test_plan_research_verify_report() -> None:
    planner, writer, coordinator = Planner(["a", "b"]), Writer(), Coordinator()
    ctx = ScriptedCtx(Children([audit([claim(1)]), audit([claim(2)])]))
    flow = make_flow(
        planner, writer, coordinator=coordinator, researcher_model="acct/small", critic_model="acct/large"
    )

    result = run(flow, ctx)

    assert planner.asked == [
        {
            "question": "What changed?",
            "max_directions": None,
            "capabilities": flow_module._capabilities(ctx),
            "operational_evidence": {"status": "available", "receipts": []},
        }
    ]
    researchers = of(ctx, "researcher")
    assert [r["key"] for r in researchers] == ["research:d1", "research:d2"]
    assert [r["input"]["direction"]["question"] for r in researchers] == ["a", "b"]
    assert {r["model"] for r in researchers} == {"acct/small"}
    # One critic per researcher, each with only its researcher's packet.
    critics = of(ctx, "critic")
    assert [c["key"] for c in critics] == ["verify:1:d1", "verify:1:d2"]
    assert [c["label"] for c in critics] == ["Check: a", "Check: b"]
    assert {c["model"] for c in critics} == {"acct/large"}
    assert [c["evidence"] for c in critics] == [["task_1"], ["task_2"]]
    assert [[p["evidence"] for p in c["input"]["packets"]] for c in critics] == [
        ["packet for a"],
        ["packet for b"],
    ]
    assert "max_gaps" not in critics[0]["input"]
    assert ctx.steps == [
        "DeepResearch._plan",
        "DeepResearch._coordinate",
        "DeepResearch._write",
        "DeepResearch._review",
    ]
    (seen,) = coordinator.given
    assert seen["rounds_left"] == 1 and seen["max_follow_ups"] is None
    assert [row["claim_id"] for row in seen["verified"]] == [
        claim(1)["claim_id"],
        claim(2)["claim_id"],
    ]
    assert seen["assignments"] == [
        {"id": "d1", "question": "a", "round": 1, "outcome": {"verified": 1, "rejected": 0}},
        {"id": "d2", "question": "b", "round": 1, "outcome": {"verified": 1, "rejected": 0}},
    ]
    assert writer.given[0]["verified"] == [claim(1), claim(2)]
    assert result["verified"] == [claim(1), claim(2)]
    assert result["rejected"] == [] and result["gaps_unresolved"] == []
    assert result["rounds"] == 1 and result["citations_outside_verified"] == []
    assert [d["id"] for d in result["directions"]] == ["d1", "d2"]
    assert [r["handle"] for r in result["researchers"]] == ["task_1", "task_2"]
    revision = flow_module._permission_revision({"status": "available", "receipts": []})
    assert result["critics"] == [
        {
            "round": 1,
            "direction": direction,
            "handle": handle,
            "model": "acct/large",
            "operational_update": False,
            "evidence_review": False,
            "source_auditors": [handle],
            "permission_revision": revision,
        }
        for direction, handle in (("d1", "task_3"), ("d2", "task_4"))
    ]
    assert "## Unresolved questions" not in result["answer"]
    assert result["answer"].startswith("# Report")


def test_a_follow_up_the_coordinator_chooses_gets_one_targeted_round() -> None:
    audits = [audit([claim(1)], gaps=[gap("who ruled?")]), audit(), audit([claim(2)])]
    ctx = ScriptedCtx(Children(audits))
    coordinator = Coordinator()

    result = run(make_flow(Planner(["a", "b"]), coordinator=coordinator), ctx)

    researchers = of(ctx, "researcher")
    assert [r["key"] for r in researchers] == ["research:d1", "research:d2", "research:g2.1"]
    assert researchers[2]["input"]["direction"]["question"] == "who ruled?"
    assert researchers[2]["input"]["round"] == 2
    third = of(ctx, "critic")[2]
    assert third["key"] == "verify:2:g2.1"
    # The follow-up's critic reads only the new packet; the ledger is merged by the flow.
    assert third["evidence"] == ["task_5"] and "earlier_audit" not in third["input"]
    assert [p["id"] for p in third["input"]["packets"]] == ["g2.1"]
    first, last = coordinator.given
    assert first["proposed_gaps"] == [gap("who ruled?")] and first["rounds_left"] == 1
    assert [row["id"] for row in last["assignments"]] == ["d1", "d2", "g2.1"]
    assert last["rounds_left"] == 0
    assert result["rounds"] == 2 and result["gaps_unresolved"] == []
    assert result["verified"] == [claim(1), claim(2)]


def test_non_web_requirements_do_not_spawn_impossible_research_rounds(tmp_path: Path) -> None:
    requirements = [
        gap(
            "Save and read back this report",
            closure_kind="workflow_action",
            required_tools=[],
            action="persist_report",
        ),
        gap("Supply the site's free space", closure_kind="external_input", required_tools=[]),
        gap(
            "Measure the private dataset",
            closure_kind="unavailable_action",
            required_tools=["shell_run"],
        ),
        gap(
            "Proposed benchmark gates await measurements",
            closure_kind="design_limit",
            required_tools=[],
        ),
        gap("Check an inaccessible file", required_tools=["fs_read"]),
    ]
    ctx = ScriptedCtx(Children([audit([claim(1)], gaps=requirements)]), workspace=tmp_path)
    writer = Writer()

    result = run(make_flow(Planner(["public evidence"]), writer), ctx)

    assert len(of(ctx, "researcher")) == len(of(ctx, "critic")) == 1
    assert result["gaps_unresolved"] == requirements[1:]
    assert result["delivery_requirements"] == requirements[:1]
    assert result["persistence"]["status"] == "verified"
    assert writer.given[0]["unresolved_gaps"] == requirements[1:]
    assert writer.given[0]["delivery"]["persist_report"]["stage"] == "after_synthesis"
    assert writer.given[0]["delivery"]["review_report"]["stage"] == "after_draft"
    assert "Save and read back" not in result["answer"]
    assert "Supply the site's free space" in result["answer"]
    assert "requires: fs_read" in result["answer"]
    assert any(e.get("missing_tools") == ["fs_read"] for e in ctx.events)


def test_planner_requirements_are_routed_using_the_actual_declared_allowlist() -> None:
    filesystem = gap("Inspect a local report", required_tools=["fs_read"])
    delivery = gap(
        "Persist the final document",
        closure_kind="workflow_action",
        required_tools=[],
        action="persist_report",
    )
    ctx = ScriptedCtx(Children([audit([claim(1)])]))
    result = run(make_flow(Planner([filesystem, delivery, "public documentation"])), ctx)
    assert [c["input"]["direction"]["question"] for c in of(ctx, "researcher")] == [
        "public documentation"
    ]
    assert [row["question"] for row in of(ctx, "critic")[0]["input"]["assignments"]] == [
        "public documentation"
    ]
    assert result["gaps_unresolved"] == [filesystem, delivery]
    assert result["persistence"]["status"] == "unavailable"

    # A missing declaration is unknown access, not permission to assume web tools.
    ctx = ScriptedCtx(Children([]))
    ctx.resolution.subagents = []
    result = run(make_flow(Planner(["public documentation"])), ctx)
    assert not ctx.calls
    assert result["rounds"] == 0
    assert result["gaps_unresolved"] == [gap("public documentation")]


def test_the_coordinator_sees_deferred_requirements_but_only_web_follow_ups_run(
    tmp_path: Path,
) -> None:
    delivery = gap(
        "Verify report persistence",
        closure_kind="workflow_action",
        required_tools=[],
        action="persist_report",
    )
    ctx = ScriptedCtx(
        Children([audit([claim(1)], gaps=[delivery, gap("contradiction")]), audit([claim(2)])]),
        workspace=tmp_path,
    )
    coordinator = Coordinator()
    result = run(make_flow(Planner(["a"]), coordinator=coordinator), ctx)
    assert [r["input"]["direction"]["question"] for r in of(ctx, "researcher")] == [
        "a",
        "contradiction",
    ]
    assert coordinator.given[0]["proposed_gaps"] == [delivery, gap("contradiction")]
    assert result["gaps_unresolved"] == []
    assert sum(s.endswith("persist_report") for s in ctx.steps) == 1


def test_delivery_failure_never_returns_a_verified_report_path(tmp_path: Path) -> None:
    class BrokenReadback(FlowWorkspace):
        def read(self, relative: str) -> str:
            return "different report"

    delivery = gap(
        "Persist report", closure_kind="workflow_action", required_tools=[], action="persist_report"
    )
    ctx = ScriptedCtx(Children([audit([claim(1)], gaps=[delivery])]))
    ctx.workspace = BrokenReadback(tmp_path)
    result = run(make_flow(Planner(["a"])), ctx)
    assert result["report_path"] == ""
    assert result["persistence"]["reason"] == "readback_mismatch"
    assert result["gaps_unresolved"] == [delivery]
    assert result["persistence"]["text_sha256"] != result["persistence"]["readback_text_sha256"]

    class DeniedWrite(FlowWorkspace):
        def write(self, relative: str, text: str) -> str:
            raise PermissionError("test write denied")

    ctx = ScriptedCtx(Children([audit()]))
    ctx.workspace = DeniedWrite(tmp_path)
    result = run(make_flow(Planner(["a"])), ctx)
    assert result["report_path"] == ""
    assert result["persistence"]["status"] == "failed"
    assert result["persistence"]["reason"] == "PermissionError"


def test_verified_delivery_replays_its_receipt_without_rewriting(tmp_path: Path) -> None:
    class CountedWorkspace(FlowWorkspace):
        writes = 0
        reads = 0

        def write(self, relative: str, text: str) -> str:
            self.writes += 1
            return super().write(relative, text)

        def read(self, relative: str) -> str:
            self.reads += 1
            return super().read(relative)

    workspace = CountedWorkspace(tmp_path)
    ctx = ScriptedCtx(Children([audit([claim(1)])]))
    ctx.workspace = workspace
    result = run(make_flow(Planner(["a"])), ctx)
    replay = ScriptedCtx(Children([]), journal=ctx.journal)
    replay.workspace = workspace
    assert run(make_flow(Planner(["a"])), replay) == result
    assert workspace.writes == workspace.reads == 1
    assert Path(result["report_path"]).read_text(encoding="utf-8") == result["answer"]


@pytest.mark.parametrize(
    "changes",
    [
        {"closure_kind": "guess"},
        {"required_tools": []},
        {"closure_kind": "workflow_action", "action": ""},
        {"action": "persist_report"},
    ],
)
def test_malformed_closure_requirements_are_not_silently_web_work(changes: dict[str, Any]) -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        gap("open", **changes)


def test_a_gap_left_open_at_the_bound_is_reported_unresolved() -> None:
    audits = [
        audit([claim(1)], gaps=[gap("who ruled?")]),
        audit([claim(1)], gaps=[gap("when?")]),
    ]
    writer = Writer()
    ctx = ScriptedCtx(Children(audits))

    result = run(make_flow(Planner(["a"]), writer, max_rounds=1), ctx)

    assert len(of(ctx, "critic")) == 2 and result["rounds"] == 2
    assert result["gaps_unresolved"] == [gap("when?")]
    assert writer.given[0]["unresolved_gaps"] == [gap("when?")]
    assert "## Unresolved questions\n\n- when? (it could change the answer)" in result["answer"]


def test_a_capped_follow_up_and_an_unanswered_requirement_stay_open() -> None:
    external = gap("Operator input", closure_kind="external_input", required_tools=[])
    pending = [external, gap("selected follow-up"), gap("capped follow-up")]
    ctx = ScriptedCtx(Children([audit([claim(1)], gaps=pending), audit([claim(1)])]))
    result = run(make_flow(Planner(["a"]), max_directions=1, max_rounds=1), ctx)
    assert result["gaps_unresolved"] == [external, gap("capped follow-up")]
    assert [r["input"]["direction"]["question"] for r in of(ctx, "researcher")] == [
        "a",
        "selected follow-up",
    ]
    (capped,) = [e for e in ctx.events if e["event"] == "follow_ups_capped"]
    assert capped["dropped"] == ["capped follow-up"]


def test_gap_closure_requires_prior_identity_and_verified_evidence_or_scope_reason() -> None:
    pending = gap("Need user quota", closure_kind="external_input", required_tools=[])
    section = audit()["workflow_state"]
    section["audit"]["resolved_gaps"] = [
        {
            "gap_id": pending["gap_id"],
            "basis": "new_evidence",
            "reason": "It was checked",
            "source_urls": ["https://unsupported.example/claim"],
        }
    ]
    result = SimpleNamespace(workflow_state=section)
    typed_pending = [flow_module.Gap.model_validate(pending)]
    assert flow_module._audit_of(result, typed_pending)[0] is None
    section["audit"]["resolved_gaps"] = [
        {
            "gap_id": pending["gap_id"],
            "basis": "scope_correction",
            "reason": "The person asked for an admission formula, not measured free capacity",
            "source_urls": [],
        }
    ]
    parsed, problems = flow_module._audit_of(result, typed_pending)
    assert not problems and parsed.gaps == []
    assert flow_module._audit_of(result, [])[0] is None


def test_unrepaired_outside_citations_are_unlinked_and_the_report_delivered(
    tmp_path: Path,
) -> None:
    writer = Writer(extra="\n[a blog](https://unsupported.example/claim)")
    ctx = ScriptedCtx(Children([audit([claim(1)])]), workspace=tmp_path)
    run(make_flow(Planner(["a"]), writer), ctx)
    assert len(writer.given) == 2  # the writer had its correction
    [persisted] = list(tmp_path.rglob("*.md"))
    text = persisted.read_text()
    assert "https://unsupported.example/claim" not in text
    assert "a blog (unverified source)" in text
    assert "## Open review notes" in text and "outside the verified evidence graph" in text
    event = next(r for r in ctx.events if r["event"] == "report_delivered_with_open_issues")
    assert event["unverified_urls"] == ["https://unsupported.example/claim"]


@pytest.mark.parametrize(
    ("grantor", "action", "tool", "input_kind", "receipt_id", "accepted"),
    [
        ("user", "allow_workspace", "web_fetch", "permission", "r1", True),
        ("user", "allow", "web_fetch", "permission", "r1", False),
        ("system", "allow_workspace", "web_fetch", "permission", "r1", False),
        ("user", "deny", "web_fetch", "permission", "r1", False),
        ("user", "allow_workspace", "shell_exec", "permission", "r1", False),
        ("user", "allow_workspace", "web_fetch", "", "r1", False),
        ("user", "allow_workspace", "web_fetch", "permission", "invented", False),
    ],
)
def test_operator_resolution_requires_receipts_for_this_specific_permission_input(
    grantor: str,
    action: str,
    tool: str,
    input_kind: str,
    receipt_id: str,
    accepted: bool,
) -> None:
    pending = flow_module.Gap.model_validate(
        gap(
            "Was this tool operation authorized?",
            closure_kind="external_input",
            required_tools=["web_fetch"],
            input_kind=input_kind,
            permission_requirement={"scope": "workspace", "scope_id": "ws_expected"}
            if input_kind
            else None,
        )
    )
    result = SimpleNamespace(
        workflow_state={
            "audit": {
                "resolved_gaps": [
                    {
                        "gap_id": pending.gap_id,
                        "basis": "operator_evidence",
                        "reason": "Historical decision, within the tool and scope recorded in the receipt",
                        "receipt_ids": [receipt_id],
                    }
                ]
            }
        }
    )
    evidence = {
        "status": "available",
        "receipts": [
            {
                "receipt_id": "r1",
                "grantor": grantor,
                "action": action,
                "tool_name": tool,
                "decision_status": "resolved",
                "kind": "external_mcp",
                "workspace_id": "ws_expected",
                "policy_scope": "workspace",
                "policy_scope_id": "ws_expected",
                "resource_restricted": False,
            }
        ],
    }
    parsed, _problems = flow_module._audit_of(result, [pending], operational_evidence=evidence)
    assert (parsed is not None) == accepted


@pytest.mark.parametrize(
    ("scope", "scope_id", "updates", "accepted"),
    [
        ("workspace", "ws_a", {}, True),
        ("workspace", "ws_b", {}, False),
        ("workspace", "ws_a", {"resource_restricted": True}, False),
        ("workspace", "ws_a", {"workspace_id": "ws_b"}, False),
        ("workspace", "ws_a", {"policy_scope_id": "ws_b"}, False),
        ("workspace", "ws_a", {"kind": "network_egress"}, False),
        ("session", "sess_a", {}, False),
        (
            "session",
            "sess_a",
            {"action": "allow_session", "policy_scope": "session", "policy_scope_id": "sess_a"},
            True,
        ),
        ("invocation", "perm_a", {"action": "allow", "resource_restricted": True}, True),
        ("invocation", "perm_b", {"action": "allow"}, False),
    ],
)
def test_permission_requirement_cannot_broaden_another_scope_or_operation(
    scope: str,
    scope_id: str,
    updates: dict[str, Any],
    accepted: bool,
) -> None:
    receipt = {
        "permission_id": "perm_a",
        "kind": "external_mcp",
        "action": "allow_workspace",
        "workspace_id": "ws_a",
        "session_id": "sess_a",
        "policy_scope": "workspace",
        "policy_scope_id": "ws_a",
        "resource_restricted": False,
        **updates,
    }
    requirement = flow_module.PermissionRequirement.model_validate(
        {"scope": scope, "scope_id": scope_id}
    )
    assert flow_module._permission_covers(receipt, requirement) == accepted


def test_audit_and_writer_receive_operational_history_without_replacing_source_evidence() -> None:
    class ReceiptCtx(ScriptedCtx):
        async def permission_receipts(self, *, refresh: bool = False) -> dict[str, Any]:
            return {
                "status": "available",
                "receipts": [
                    {
                        "receipt_id": "historic-timeout",
                        "action": "deny",
                        "grantor": "system",
                        "reason": "permission_request_timeout",
                    }
                ],
            }

    writer = Writer()
    ctx = ReceiptCtx(Children([audit([claim(1)])]))
    result = run(make_flow(Planner(["a"]), writer), ctx)
    assert (
        of(ctx, "critic")[0]["input"]["operational_evidence"]["receipts"][0]["receipt_id"]
        == "historic-timeout"
    )
    assert writer.given[0]["verified"] == [claim(1)]
    assert writer.given[0]["operational_evidence"] == result["operational_evidence"]


def test_late_consent_opens_a_new_audit_boundary_without_repeating_research() -> None:
    requirement = gap(
        "May this workspace retry the tool?",
        closure_kind="external_input",
        required_tools=["web_fetch"],
        input_kind="permission",
        permission_requirement={"scope": "workspace", "scope_id": "ws_a"},
    )
    receipt = {
        "receipt_id": "r1",
        "permission_id": "perm_a",
        "kind": "external_mcp",
        "grantor": "user",
        "action": "allow_workspace",
        "decision_status": "resolved",
        "tool_name": "web_fetch",
        "workspace_id": "ws_a",
        "policy_scope": "workspace",
        "policy_scope_id": "ws_a",
        "resource_restricted": False,
    }
    closed = audit()
    closed["workflow_state"]["audit"]["resolved_gaps"] = [
        {
            "gap_id": requirement["gap_id"],
            "basis": "operator_evidence",
            "reason": "The later human grant covers this workspace tool requirement",
            "receipt_ids": ["r1"],
        }
    ]

    class LateConsentCtx(ScriptedCtx):
        async def permission_receipts(self, *, refresh: bool = False) -> dict[str, Any]:
            return {"status": "available", "receipts": [receipt] if refresh else []}

    ctx = LateConsentCtx(Children([audit([claim(1)], gaps=[requirement]), closed]))
    result = run(make_flow(Planner(["a"])), ctx)
    assert len(of(ctx, "researcher")) == 1
    assert len(of(ctx, "critic")) == 2
    update = of(ctx, "critic")[1]["input"]
    assert update["operational_update"] is True and update["packets"] == []
    assert update["earlier_audit"]["verified"] == [claim(1)]
    assert result["verified"] == [claim(1)] and result["gaps_unresolved"] == []
    assert result["critics"][-1]["operational_update"] is True


def test_planner_can_ground_an_explicit_permission_requirement_in_its_own_scope() -> None:
    class ScopedCtx(ScriptedCtx):
        async def permission_receipts(self, *, refresh: bool = False) -> dict[str, Any]:
            return {
                "status": "available",
                "receipts": [],
                "scope": {
                    "workspace_id": "ws_real",
                    "session_id": "sess_real",
                    "assignment_id": "task_real",
                },
            }

    class ScopePlanner(Planner):
        def __call__(self, **kwargs: Any) -> Any:
            self.questions = [
                gap(
                    "Requested confirmation of workspace approval",
                    closure_kind="external_input",
                    input_kind="permission",
                    required_tools=["web_fetch"],
                    permission_requirement={
                        "scope": "workspace",
                        "scope_id": kwargs["operational_evidence"]["scope"]["workspace_id"],
                    },
                )
            ]
            return super().__call__(**kwargs)

    planner = ScopePlanner([])
    result = run(make_flow(planner), ScopedCtx(Children([])))
    assert result["gaps_unresolved"][0]["permission_requirement"]["scope_id"] == "ws_real"
    assert planner.asked[0]["operational_evidence"]["scope"]["assignment_id"] == "task_real"


def test_an_empty_report_cannot_receive_a_verified_delivery_receipt(tmp_path: Path) -> None:
    flow = make_flow(Planner(["a"]))
    flow.writer = lambda **kwargs: dspy.Prediction(blocks=[])
    ctx = ScriptedCtx(Children([audit([claim(1)])]), workspace=tmp_path)
    with pytest.raises(FlowStall) as stalled:
        run(flow, ctx)
    assert stalled.value.stall == "report_empty"
    assert not list(tmp_path.rglob("*.md"))


def test_prior_claims_cannot_disappear_without_an_explicit_audit_update() -> None:
    rejected = {"claim": "unsupported", "reason": "no primary source", "source_url": ""}
    earlier = flow_module.Audit.model_validate(
        audit([claim(1)], [rejected])["workflow_state"]["audit"]
    )
    result = SimpleNamespace(workflow_state=audit()["workflow_state"])
    parsed, problems = flow_module._audit_of(result, [], earlier)
    assert not problems
    assert [c.model_dump() for c in parsed.verified] == [claim(1)]
    assert [c.model_dump() for c in parsed.rejected] == [rejected]

    withdrawal = {
        "claim": claim(1)["claim"],
        "source_url": claim(1)["evidence"][0]["source_url"],
        "reason": "The source now retracts it",
    }
    result.workflow_state = audit(rejected=[withdrawal])["workflow_state"]
    parsed, problems = flow_module._audit_of(result, [], earlier)
    assert not problems and not parsed.verified
    assert [c.model_dump() for c in parsed.rejected] == [withdrawal, rejected]


@pytest.mark.parametrize("max_rounds", [0, 1, 2, 3])
def test_max_rounds_bounds_the_follow_up_rounds(max_rounds: int) -> None:
    audits = [audit([claim(1)], gaps=[gap(f"open {n}")]) for n in range(10)]
    ctx = ScriptedCtx(Children(audits))
    coordinator = Coordinator()

    result = run(make_flow(Planner(["a"]), coordinator=coordinator, max_rounds=max_rounds), ctx)

    assert len(of(ctx, "critic")) == max_rounds + 1
    assert len(of(ctx, "researcher")) == max_rounds + 1
    assert result["rounds"] == max_rounds + 1
    assert [row["rounds_left"] for row in coordinator.given] == list(range(max_rounds, -1, -1))
    assert result["gaps_unresolved"] == [gap(f"open {max_rounds}")]


def test_max_directions_caps_the_plan_and_each_gap_round() -> None:
    planner = Planner([f"q{n}" for n in range(1, 6)])
    audits = [audit(gaps=[gap(f"g{n}") for n in range(1, 5)]), audit()]
    ctx = ScriptedCtx(Children(audits))

    coordinator = Coordinator()
    result = run(make_flow(planner, coordinator=coordinator, max_directions=3, max_rounds=1), ctx)

    assert planner.asked[0]["max_directions"] == 3
    assert coordinator.given[0]["max_follow_ups"] == 3
    assert [r["key"] for r in of(ctx, "researcher")] == [
        "research:d1",
        "research:d2",
        "research:d3",
        "research:g2.1",
        "research:g2.2",
        "research:g2.3",
    ]
    assert [d["question"] for d in result["directions"]] == ["q1", "q2", "q3"]
    assert [e for e in ctx.events if e["event"].endswith("_capped")] == [
        {"event": "directions_capped", "round": 0, "asked": 5, "kept": 3, "dropped": ["q4", "q5"]},
        {"event": "follow_ups_capped", "round": 2, "asked": 4, "kept": 3, "dropped": ["g4"]},
    ]


def test_the_report_is_written_only_from_verified_claims() -> None:
    rejected = {"claim": "the moon is cheese", "reason": "no source supports it", "source_url": ""}
    writer = Writer(extra="\n\nSee also [a blog](https://blog.example.net/post).", repairable=True)
    ctx = ScriptedCtx(Children([audit([claim(1)], rejected=[rejected])]))

    result = run(make_flow(Planner(["a"]), writer), ctx)

    given = json.dumps(writer.given)
    assert "the moon is cheese" not in given
    assert writer.given[0]["verified"] == [claim(1)]
    report, record = result["answer"].split("## Rejected claims", 1)
    assert "the moon is cheese" not in report
    assert "- the moon is cheese: no source supports it" in record
    assert result["rejected"] == [rejected]
    # The model corrects its draft once; an unverified citation is not delivered.
    assert result["citations_outside_verified"] == []
    assert result["rejected_draft_citations"] == ["https://blog.example.net/post"]
    assert len(writer.given) == 2
    assert {
        "event": "report_cites_unverified_source",
        "urls": ["https://blog.example.net/post"],
    } in (ctx.events)
    assert "https://blog.example.net/post" not in result["answer"]


def test_the_report_is_written_to_the_workspace_and_typed_for_the_caller(tmp_path: Path) -> None:
    ctx = ScriptedCtx(Children([audit([claim(1)], gaps=[gap("open")])]), workspace=tmp_path)

    result = run(make_flow(Planner(["a"]), max_rounds=0), ctx, "Why did the rule change?")

    path = Path(result["report_path"])
    assert path == tmp_path / "deep-research" / "why-did-the-rule-change-89abcdef.md"
    assert path.read_text(encoding="utf-8") == result["answer"]
    assert ctx.steps[-1] == "DeepResearch.forward.<locals>.persist_report"
    typed = result["workflow_state"]["deep_research"]
    assert typed["report_path"] == str(path) and typed["verified"] == [claim(1)]
    assert typed["gaps_unresolved"] == [gap("open")] and typed["rounds"] == 1
    assert typed["persistence"]["status"] == "verified"
    assert typed["persistence"]["text_sha256"] == typed["persistence"]["readback_text_sha256"]
    delivery = typed["delivery"]
    assert delivery["report_path"] == str(path)
    assert delivery["used"] == [claim(1)["evidence"][0]["source_url"]]
    assert delivery["verified_count"] == 1 and delivery["rejected_count"] == 0
    assert delivery["gaps_unresolved"] == typed["gaps_unresolved"]
    assert delivery["report_review"]["report_sha256"] == typed["persistence"]["text_sha256"]

    ctx = ScriptedCtx(Children([audit([claim(1)])]))
    assert run(make_flow(Planner(["a"])), ctx)["report_path"] == ""
    assert {"event": "report_not_written", "reason": "no_workspace"} in ctx.events


def test_replay_reattaches_to_the_same_calls_and_steps() -> None:
    def fresh() -> Children:
        return Children(
            [audit([claim(1)], gaps=[gap("open")]), audit([claim(1), claim(2)], resolved=["open"])]
        )

    first = ScriptedCtx(fresh())
    result = run(make_flow(Planner(["a", "b"])), first)

    # Same results: the same calls, in the same order, with the same keys and inputs.
    again = ScriptedCtx(fresh())
    assert run(make_flow(Planner(["a", "b"])), again) == result
    assert again.calls == first.calls

    # A replay over the journal: no model step runs again and no call is resubmitted.
    def no_children(target: str, payload: Any) -> dict[str, Any]:
        raise AssertionError(f"{target} was resubmitted on replay")

    planner, writer = Planner(["different"]), Writer()
    replay = ScriptedCtx(no_children, journal=first.journal)
    assert run(make_flow(planner, writer), replay) == result
    assert replay.calls == first.calls
    assert planner.asked == [] and writer.given == []


def test_delivery_uses_only_cited_claims_but_counts_the_entire_audit() -> None:
    audit_model = flow_module.Audit.model_validate(
        audit([claim(1), claim(2)])["workflow_state"]["audit"]
    )
    blocks = [
        {"text": "Only this claim.", "kind": "source_fact", "claim_ids": [claim(2)["claim_id"]]}
    ]
    reviews = [{"status": "accepted_by_reviewer", "report_sha256": "exact-document"}]
    delivery = flow_module.delivery_record(
        audit_model,
        blocks,
        reviews,
        {"status": "unavailable", "path": "", "reason": "no_workspace"},
        [],
    )
    assert delivery["report_path"] == ""
    assert delivery["used"] == [claim(2)["evidence"][0]["source_url"]]
    assert delivery["verified_count"] == 2
    assert delivery["report_review"] == reviews[-1]


def test_an_audit_off_schema_is_restated_once_then_stalls() -> None:
    bad = {"answer": "audit", "workflow_state": {"audit": {"verified": [{"claim": "x"}]}}}
    ctx = ScriptedCtx(Children([bad, audit([claim(1)])]))

    result = run(make_flow(Planner(["a"])), ctx)

    first, repair = of(ctx, "critic")
    assert repair["key"] == "verify:1:d1:repair" and repair["evidence"] == ["task_2"]
    assert any("evidence" in problem for problem in repair["input"]["repair"])
    assert result["verified"] == [claim(1)]

    ctx = ScriptedCtx(Children([bad, {"answer": "still prose"}]))
    with pytest.raises(FlowStall) as stalled:
        run(make_flow(Planner(["a"])), ctx)
    assert stalled.value.stall == "critic_audit_invalid"


@pytest.mark.parametrize("field", ["quote", "supports", "task_handle"])
def test_source_edges_cannot_use_blank_integrity_fields(field: str) -> None:
    row = claim(1)
    row["evidence"][0][field] = " \n\t "
    with pytest.raises(ValueError, match="must not be blank"):
        flow_module.VerifiedClaim.model_validate(row)


@pytest.mark.parametrize(
    "failure",
    ["failed", "server_error", "empty", "other_actor", "wrong_server", "accepted", "error_flag"],
)
def test_only_actual_successful_critic_fetches_can_bind_a_source(failure: str) -> None:
    row = source_fixture(1, "critic")
    if failure == "failed":
        row["task"]["status"] = "failed"
    elif failure == "server_error":
        row["value"]["status"] = 503
    elif failure == "empty":
        row["value"]["content"] = " "
    elif failure == "other_actor":
        row["task"]["owner"]["assignment_id"] = "researcher"
    elif failure == "wrong_server":
        row["task"]["backend"]["server"] = "other"
    elif failure == "accepted":
        row["value"] = {"status": "running", "result": row["value"]}
    else:
        row["value"] = {"isError": True, "structuredContent": row["value"]}
    assert flow_module.source_records([row], {"critic"}) == {}


def test_source_binding_checks_actual_url_quote_and_unique_occurrence() -> None:
    records = flow_module.source_records([source_fixture(1, "critic")], {"critic"})
    wrong_url = flow_module.VerifiedClaim.model_validate(claim(1))
    wrong_url.evidence[0].source_url += "?different=query"
    assert "fetched resource" in flow_module.bind_claims([wrong_url], records)[0]
    wrong_quote = flow_module.VerifiedClaim.model_validate(claim(1))
    wrong_quote.evidence[0].quote = "a plausible passage not actually fetched"
    assert "absent" in flow_module.bind_claims([wrong_quote], records)[0]
    row = source_fixture(1, "critic")
    row["value"]["content"] = "passage 1 in section A. passage 1 in section B."
    records = flow_module.source_records([row], {"critic"})
    ambiguous = flow_module.VerifiedClaim.model_validate(claim(1))
    assert "repeats" in flow_module.bind_claims([ambiguous], records)[0]
    ambiguous.evidence[0].quote = "passage 1 in section B."
    assert flow_module.bind_claims([ambiguous], records) == []


def test_an_inline_builtin_fetch_binds_by_its_call_reference() -> None:
    """In-process web fetches answer inline: no adopted backend, cited by call reference."""
    row = source_fixture(1, "critic")
    row["task"]["backend"] = None
    row["task"]["submitted_backend"] = {"owner": "external_mcp", "server": "web"}
    row["task"]["invocation_id"] = "call_8f73cc6042d7"
    records = flow_module.source_records([row], {"critic"})
    assert list(records) == ["fetch_1"]
    for cited in (
        "call:sess_abc/call_8f73cc6042d7",
        "[call:sess_abc/call_8f73cc6042d7]",
        "call_8f73cc6042d7",
    ):
        bound = flow_module.VerifiedClaim.model_validate(claim(1))
        bound.evidence[0].task_handle = cited
        assert flow_module.bind_claims([bound], records) == []
        assert bound.evidence[0].task_handle == "fetch_1"
    unknown = flow_module.VerifiedClaim.model_validate(claim(1))
    unknown.evidence[0].task_handle = "call_68b7df5f_5"  # the model's own tool-call id
    assert "no successful critic-owned fetch" in flow_module.bind_claims([unknown], records)[0]
    other = source_fixture(2, "critic")
    other["task"]["backend"] = None
    other["task"]["submitted_backend"] = {"owner": "external_mcp", "server": "files"}
    assert flow_module.source_records([other], {"critic"}) == {}


def test_merging_a_proposition_keeps_every_supporting_document() -> None:
    first = claim(1)
    second = claim(2)
    first["claim"] = second["claim"] = "Joint proposition from two documents"
    first["claim_id"] = second["claim_id"] = ""
    merged = flow_module.merge_claims(
        [flow_module.VerifiedClaim.model_validate(row) for row in [first, second]]
    )
    assert len(merged) == 1 and len(merged[0].evidence) == 2
    report = flow_module.ReportBlock(
        text="Joint proposition from two documents",
        kind="source_fact",
        claim_ids=[merged[0].claim_id],
    )
    evidence_module = import_plugin_module(PLUGIN, "evidence.py")
    rendered = evidence_module.render_report([report], merged)
    assert "https://example.org/1" in rendered and "https://example.org/2" in rendered


def test_review_context_retains_source_line_structure_and_declares_window_bounds() -> None:
    module = import_plugin_module(PLUGIN, "evidence.py")
    row = source_fixture(1, "critic")
    row["value"]["content"] = (
        "Prefix\n" + "x" * 1000 + "\n```python\n    passage 1\n```\n" + "y" * 1000
    )
    records = flow_module.source_records([row], {"critic"})
    claims = [flow_module.VerifiedClaim.model_validate(claim(1))]
    assert flow_module.bind_claims(claims, records) == []
    context = module.review_sources(claims, records)[0]["passage_context"][0]
    assert "```python\n    passage 1\n```" in context["text"]
    assert context["context_complete"] is False
    assert context["coordinates"] == "source_text_characters"
    assert (
        row["value"]["content"][context["context_start"] : context["context_end"]]
        == context["text"]
    )


def test_rendered_citations_do_not_break_code_blocks_or_reparse_source_titles() -> None:
    module = import_plugin_module(PLUGIN, "evidence.py")
    claim_row = flow_module.VerifiedClaim.model_validate(claim(1))
    claim_row.evidence[0].source_title = "Xarray_to_zarr [API]"
    block = flow_module.ReportBlock(
        text="```python\nprint('example')\n```", kind="proposal", claim_ids=[claim_row.claim_id]
    )
    rendered = module.render_report([block], [claim_row])
    assert "\n```\n\n[Xarray\\_to\\_zarr \\[API\\]]" in rendered


def test_semantic_contradiction_is_corrected_and_review_covers_the_saved_document(
    tmp_path: Path,
) -> None:
    stale = "No fresh sources were fetched."
    issue = {
        "owner": "report",
        "excerpt": stale,
        "reason": "Contradicts a current-run successful bound source",
        "claim_ids": [claim(1)["claim_id"]],
    }
    reviewer = Reviewer([[issue], []])
    writer = Writer(extra=stale, repairable=True)
    ctx = ScriptedCtx(Children([audit([claim(1)])]), workspace=tmp_path)
    result = run(make_flow(Planner(["a"]), writer, reviewer), ctx)
    assert stale not in result["answer"]
    assert len(writer.given) == len(reviewer.given) == 2
    assert reviewer.given[0]["source_records"][0]["http_status"] == 200
    assert result["report_reviews"][0]["issues"] == [issue]
    assert result["report_reviews"][-1]["status"] == "accepted_by_reviewer"
    assert result["report_reviews"][-1]["report_sha256"] == result["persistence"]["text_sha256"]


def test_semantic_audit_fault_returns_to_critic_without_losing_source_edges() -> None:
    compound = claim(1)
    compound["claim"] = "claim 1 and claim 2"
    compound["claim_id"] = ""
    compound = flow_module.VerifiedClaim.model_validate(compound).model_dump()
    # Its quote is genuinely in source1, but that alone does not support the second clause.
    issue = {
        "owner": "audit",
        "excerpt": compound["claim"],
        "reason": "The second clause has no supporting source edge",
        "claim_ids": [compound["claim_id"]],
    }
    correction = audit(
        [claim(1), claim(2)],
        rejected=[
            {
                "claim": compound["claim"],
                "reason": "Only partial support; replaced with two atoms",
                "source_url": compound["evidence"][0]["source_url"],
            }
        ],
    )
    ctx = ScriptedCtx(Children([audit([compound]), correction]))
    result = run(make_flow(Planner(["a"]), reviewer=Reviewer([[issue], []])), ctx)
    assert result["verified"] == [claim(1), claim(2)]
    assert result["critics"][-1]["evidence_review"] is True
    assert of(ctx, "critic")[1]["input"]["evidence_review"] == [issue]
    assert len(result["sources"]) == 2


def test_unresolved_semantic_fault_is_delivered_with_its_open_notes(tmp_path: Path) -> None:
    issue = {
        "owner": "report",
        "excerpt": "unsupported connective",
        "reason": "The report is still stronger than its mapped claims",
        "claim_ids": [],
    }
    ctx = ScriptedCtx(Children([audit([claim(1)])]), workspace=tmp_path)
    result = run(make_flow(Planner(["a"]), reviewer=Reviewer([[issue], [issue]])), ctx)
    [persisted] = list(tmp_path.rglob("*.md"))
    text = persisted.read_text()
    assert "## Open review notes" in text
    assert "The report is still stronger than its mapped claims" in text
    assert result["report_reviews"][-1]["status"] == "delivered_with_open_issues"
    assert result["report_reviews"][-1]["report_sha256"] == result["persistence"]["text_sha256"]


def test_source_repair_reobserves_the_original_auditor_without_inventing_fetch_success() -> None:
    class LateResultCtx(ScriptedCtx):
        def __init__(self) -> None:
            super().__init__(Children([audit([claim(1)]), audit([claim(1)])]))
            self.reads: dict[str, int] = {}

        async def tool_results(self, handle: str) -> list[dict[str, Any]]:
            self.reads[handle] = self.reads.get(handle, 0) + 1
            if self.reads[handle] == 1 and handle == "task_2":
                return []  # No confirmed terminal source at this observation point.
            return await super().tool_results(handle)

    ctx = LateResultCtx()
    result = run(make_flow(Planner(["a"])), ctx)
    assert ctx.reads["task_2"] == 2
    assert len(of(ctx, "researcher")) == 1
    assert result["verified"] == [claim(1)]


def test_a_failed_researcher_reaches_the_coordinator_and_all_failing_ends_the_run() -> None:
    ctx = ScriptedCtx(Children([audit(gaps=[gap("b again")])], fail={"b"}))
    coordinator = Coordinator()
    result = run(make_flow(Planner(["a", "b"]), coordinator=coordinator, max_rounds=0), ctx)
    # A failed researcher has nothing to check: only the other one gets a critic.
    (critic,) = of(ctx, "critic")
    assert [p["id"] for p in critic["input"]["packets"]] == ["d1"]
    assert critic["evidence"] == ["task_1"]
    assert coordinator.given[0]["assignments"][1]["outcome"] == {"failed": "call_failed"}
    assert result["researchers"][1]["failed"]["reason"] == "call_failed"

    ctx = ScriptedCtx(Children([], fail={"a", "b"}))
    with pytest.raises(GatherFailed):
        run(make_flow(Planner(["a", "b"])), ctx)
    assert of(ctx, "critic") == []

    # A follow-up round whose researchers all fail keeps the ledger; the coordinator
    # sees the failure and says what stays open.
    decisions = [{"follow_ups": [gap("b")]}, {"open_questions": [gap("b")]}]
    ctx = ScriptedCtx(Children([audit([claim(1)])], fail={"b"}))
    coordinator = Coordinator(decisions)
    result = run(make_flow(Planner(["a"]), coordinator=coordinator, max_rounds=1), ctx)
    assert len(of(ctx, "critic")) == 1
    assert coordinator.given[1]["assignments"][1]["outcome"] == {"failed": "call_failed"}
    assert result["verified"] == [claim(1)] and result["gaps_unresolved"] == [gap("b")]


def test_no_directions_is_a_typed_stall() -> None:
    with pytest.raises(FlowStall) as stalled:
        run(make_flow(Planner([])), ScriptedCtx(Children([])))
    assert stalled.value.stall == "planner_no_directions"


def test_concurrency_bounds_researchers_in_flight() -> None:
    planner = Planner([f"q{n}" for n in range(6)])
    ctx = ScriptedCtx(Children([audit()]))
    run(make_flow(planner, concurrency=2), ctx)
    assert ctx.most_in_flight == 2

    ctx = ScriptedCtx(Children([audit()]))
    run(make_flow(planner), ctx)
    assert ctx.most_in_flight == 6


def test_options_are_checked_before_a_run_starts() -> None:
    assert DeepResearch.checked_options({"max_directions": "3", "critic_model": "a/b"}) == {
        "max_directions": 3,
        "critic_model": "a/b",
    }
    for bad, named in [
        ({"max_directions": "many"}, "max_directions must be int"),
        ({"max_rounds": True}, "max_rounds must be int"),
        ({"researcher_model": 3}, "researcher_model must be str"),
        ({"max_rounds": 9}, "max_rounds must be between 0 and 5"),
        ({"max_directions": 40}, "max_directions must be between 0 and 20"),
        ({"concurrency": -1}, "concurrency must be between 0 and 20"),
        ({"max_direction": 2}, "max_direction is not an option"),
    ]:
        with pytest.raises(FlowOptionsInvalid) as refused:
            DeepResearch.checked_options(bad)
        assert any(named in problem for problem in refused.value.problems), refused.value


def test_the_flow_declares_its_id_description_and_shape() -> None:
    assert DeepResearch.id == "deep-research"
    for option in ("max_directions", "max_rounds", "concurrency", "researcher_model"):
        assert option in DeepResearch.description
    assert DeepResearch.shape.startswith("railroad-beta\ndeep_research = sequence(")


def test_coordinator_fragments_are_main_only_mission_first_and_in_budget() -> None:
    fragments = sorted(PROMPT.glob("*.md"))
    assert [p.name for p in fragments] == ["mission.md", "options.md", "report.md"]
    for fragment in fragments:
        head, body = fragment.read_text(encoding="utf-8").split("---", 2)[1:]
        assert re.search(r'^when: \{"tools": \["run_flow"\]\}$', head, re.M), fragment.name
        assert (len(body.strip()) + 3) // 4 <= 150, fragment.name


def test_the_critic_declares_the_typed_audit_channel() -> None:
    text = (PLUGIN / "ai.iowarp.clio" / "subagents" / "critic.py").read_text(encoding="utf-8")
    assert 'structured_outputs={"workflow_state": True}' in text
    prompt = (PROMPT / "subagents" / "critic.md").read_text(encoding="utf-8")
    for field in ("workflow_state.audit", '"source_url"', '"quote"', '"reason"', '"question"'):
        assert field in prompt


def test_references_carry_the_bibliography_of_works_the_literature_tools_returned() -> None:
    """A cited arXiv or DOI page is written with its authors, year, venue and DOI."""
    evidence_module = import_plugin_module(PLUGIN, "evidence.py")
    work = {
        "title": "Lossy Compression for Scientific Data",
        "ids": {"doi": "10.1109/ipdps.2023.104", "arxiv": "2410.23497v2"},
        "authors": ["A. Liang", "B. Di", "C. Tao", "et al."],
        "year": 2023,
        "venue": "IPDPS",
        "readable_url": "https://arxiv.org/html/2410.23497v2",
    }
    lookup = {
        "task": {
            "status": "completed",
            "backend": None,
            "submitted_backend": {"server": "literature"},
        },
        "value": {"structuredContent": {"ok": True, "work": work}},
    }
    elsewhere = {**lookup, "task": {**lookup["task"], "submitted_backend": {"server": "web"}}}
    papers = evidence_module.paper_records([lookup, elsewhere])
    assert evidence_module.paper_for("https://arxiv.org/abs/2410.23497", papers) is not None
    assert evidence_module.paper_for("https://doi.org/10.1109/ipdps.2023.104", papers)
    assert evidence_module.paper_for("https://example.org/other", papers) is None
    cited = flow_module.VerifiedClaim.model_validate(claim(1))
    cited.evidence[0].source_url = "https://arxiv.org/pdf/2410.23497"
    block = flow_module.ReportBlock(text="A fact.", kind="source_fact", claim_ids=[cited.claim_id])
    rendered = evidence_module.render_report([block], [cited], papers)
    reference = rendered.split("## References\n\n", 1)[1]
    assert reference.startswith("- A. Liang, B. Di, C. Tao et al. (2023). [Lossy Compression")
    assert "*IPDPS*." in reference and reference.endswith("doi:10.1109/ipdps.2023.104")
    plain = evidence_module.render_report([block], [cited])
    assert plain.split("## References\n\n", 1)[1].startswith("- [Source 1]")


def test_unset_limit_lets_the_planner_size_the_run_and_names_each_child() -> None:
    named = [
        {**gap("What is PTC?"), "name": "Anthropic PTC docs"},
        {**gap("How is script provenance traced?"), "name": ""},
    ]
    planner = Planner(named)
    ctx = ScriptedCtx(Children([audit()]))

    run(make_flow(planner), ctx)

    assert planner.asked[0]["max_directions"] is None
    researchers = of(ctx, "researcher")
    assert [r["label"] for r in researchers] == [
        "Anthropic PTC docs",
        "How is script provenance traced?",
    ]
    assert "max_gaps" not in of(ctx, "critic")[0]["input"]
    assert not [e for e in ctx.events if e.get("event") == "directions_capped"]


def test_the_backstop_cuts_only_a_runaway_plan() -> None:
    planner = Planner([f"q{n}" for n in range(1, 41)])
    ctx = ScriptedCtx(Children([audit()]))

    run(make_flow(planner), ctx)

    assert len(of(ctx, "researcher")) == flow_module.DIRECTIONS_BACKSTOP
    (capped,) = [e for e in ctx.events if e.get("event") == "directions_capped"]
    assert capped["asked"] == 40 and capped["kept"] == flow_module.DIRECTIONS_BACKSTOP


def test_a_long_unnamed_question_is_shortened_at_a_word() -> None:
    label = flow_module._child_label(
        {"id": "g2.1", "question": "What do the OpenTelemetry GenAI semantic conventions specify?"}
    )
    assert label == "What do the OpenTelemetry GenAI semantic…"


def test_only_the_coordinator_sends_follow_ups() -> None:
    # Critics propose; a coordinator that sees nothing worth researching ends the run.
    ctx = ScriptedCtx(Children([audit([claim(1)], gaps=[gap("worth a look?")])]))
    coordinator = Coordinator([{"open_questions": [gap("worth a look?")]}])
    result = run(make_flow(Planner(["a"]), coordinator=coordinator, max_rounds=2), ctx)
    assert [r["key"] for r in of(ctx, "researcher")] == ["research:d1"]
    assert result["rounds"] == 1 and result["gaps_unresolved"] == [gap("worth a look?")]
    (event,) = [e for e in ctx.events if e["event"] == "coordinated"]
    assert event["follow_ups"] == [] and event["rounds_left"] == 2


def test_follow_ups_that_cannot_run_stay_open_questions() -> None:
    local = gap("read the lab notebook", required_tools=["fs_read"])
    late = gap("one more angle")
    ctx = ScriptedCtx(Children([audit([claim(1)])]))
    coordinator = Coordinator([{"follow_ups": [local]}, {"follow_ups": [late]}])
    result = run(make_flow(Planner(["a"]), coordinator=coordinator, max_rounds=0), ctx)
    # rounds_left is 0: every follow-up it still asks for is an open question.
    assert [r["key"] for r in of(ctx, "researcher")] == ["research:d1"]
    assert result["gaps_unresolved"] == [local]
    assert [e["event"] for e in ctx.events if e["event"].startswith("follow_ups")] == [
        "follow_ups_after_last_round"
    ]

    ctx = ScriptedCtx(Children([audit([claim(1)])]))
    coordinator = Coordinator([{"follow_ups": [local, late]}, {}])
    result = run(make_flow(Planner(["a"]), coordinator=coordinator, max_rounds=1), ctx)
    assert [r["input"]["direction"]["question"] for r in of(ctx, "researcher")] == [
        "a",
        "one more angle",
    ]
    (refused,) = [e for e in ctx.events if e["event"] == "follow_ups_not_researchable"]
    assert refused["questions"] == ["read the lab notebook"]


def test_across_reaches_the_writer_only_on_verified_claims() -> None:
    finding = {
        "kind": "corroboration",
        "statement": "Two independent sources agree",
        "claim_ids": [claim(1)["claim_id"], "claim_invented"],
    }
    writer = Writer()
    ctx = ScriptedCtx(Children([audit([claim(1)])]))
    coordinator = Coordinator([{"across": [finding]}])
    result = run(make_flow(Planner(["a"]), writer, coordinator=coordinator, max_rounds=0), ctx)
    kept = {**finding, "claim_ids": [claim(1)["claim_id"]]}
    assert writer.given[0]["across"] == [kept] and result["across"] == [kept]
    (cut,) = [e for e in ctx.events if e["event"] == "across_unverified_claims"]
    assert cut["cut"] == [
        {"statement": "Two independent sources agree", "unknown_claim_ids": ["claim_invented"]}
    ]


def test_critics_run_together_and_a_failed_critic_leaves_the_rest() -> None:
    class Slow(Children):
        def __call__(self, target: str, payload: Any) -> dict[str, Any]:
            packets = payload.get("packets") or [{}]
            if target == "critic" and (packets[0].get("id") == "d2" or "repair" in payload):
                return {"answer": "prose, no audit"}
            return super().__call__(target, payload)

    ctx = ScriptedCtx(Slow([audit([claim(1)]), audit([claim(3)])]))
    coordinator = Coordinator()
    result = run(make_flow(Planner(["a", "b", "c"]), coordinator=coordinator, max_rounds=0), ctx)
    assert ctx.most_in_flight >= 2
    assert result["verified"] == [claim(1), claim(3)]
    outcomes = [row["outcome"] for row in coordinator.given[0]["assignments"]]
    assert outcomes[1] == {"check_failed": "critic_audit_invalid"}
    (failed,) = [e for e in ctx.events if e["event"] == "check_failed"]
    assert failed["direction"] == "d2"




def test_a_failed_coordinator_keeps_the_evidence_and_leaves_proposals_open() -> None:
    class Broken(Coordinator):
        def __call__(self, **kwargs: Any) -> Any:
            raise ValueError("the reply was not the declared shape")

    ctx = ScriptedCtx(Children([audit([claim(1)], gaps=[gap("left open")])]))
    result = run(make_flow(Planner(["a"]), coordinator=Broken(), max_rounds=2), ctx)
    assert [r["key"] for r in of(ctx, "researcher")] == ["research:d1"]
    assert result["verified"] == [claim(1)] and result["gaps_unresolved"] == [gap("left open")]
    (failed,) = [e for e in ctx.events if e["event"] == "coordinator_failed"]
    assert failed["reason"] == "ValueError: the reply was not the declared shape"


def test_a_url_inside_a_fetched_title_is_neither_flagged_nor_printed_whole() -> None:
    # 2026-11-14: an arXiv page's title carried its funding note and a DOE URL. The
    # flow printed it as the citation label, then flagged the URL as the writer's.
    title = (
        "PROV-AGENT: Unified Provenance Thanks: Cite this paper as ... The DOE will "
        "provide public access in accordance with the DOE Public Access Plan "
        "(http://energy.gov/downloads/doe-public-access-plan)."
    )
    titled = claim(1)
    titled["evidence"][0]["source_title"] = title

    class Titled(Children):
        def __call__(self, target: str, payload: Any) -> dict[str, Any]:
            if target == "critic":
                return audit([titled])
            return super().__call__(target, payload)

    class TitledCtx(ScriptedCtx):
        async def tool_results(self, handle: str) -> list[dict[str, Any]]:
            rows = await super().tool_results(handle)
            for row in rows:
                row["value"]["title"] = title
            return rows

    ctx = TitledCtx(Titled([]))
    result = run(make_flow(Planner(["a"]), max_rounds=0), ctx)
    assert result["citations_outside_verified"] == []
    assert [r["status"] for r in result["report_reviews"]] == ["accepted_by_reviewer"]
    assert "energy.gov" not in result["answer"]
    assert "[PROV-AGENT: Unified Provenance Thanks: Cite this paper as" in result["answer"]
