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
    ) -> _Call:  # noqa: A002 - ctx.call's public parameter name
        row = {
            "target": target,
            "input": json.loads(json.dumps(input)),
            "evidence": list(evidence or []),
            "key": key,
            "model": model,
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
            return self.audits.pop(0)
        raise AssertionError(f"unexpected target {target}")


def make_flow(
    planner: Planner, writer: Writer | None = None, reviewer: Reviewer | None = None, **options: Any
) -> Any:
    flow = DeepResearch()
    for key, value in DeepResearch.checked_options(options).items():
        setattr(flow, key, value)
    flow.planner = planner
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
    planner, writer = Planner(["a", "b"]), Writer()
    ctx = ScriptedCtx(Children([audit([claim(1), claim(2)])]))
    flow = make_flow(planner, writer, researcher_model="acct/small", critic_model="acct/large")

    result = run(flow, ctx)

    assert planner.asked == [
        {
            "question": "What changed?",
            "max_directions": 6,
            "capabilities": flow_module._capabilities(ctx),
            "operational_evidence": {"status": "available", "receipts": []},
        }
    ]
    researchers = of(ctx, "researcher")
    assert [r["key"] for r in researchers] == ["research:d1", "research:d2"]
    assert [r["input"]["direction"]["question"] for r in researchers] == ["a", "b"]
    assert {r["model"] for r in researchers} == {"acct/small"}
    (critic,) = of(ctx, "critic")
    assert critic["key"] == "verify:1" and critic["model"] == "acct/large"
    assert critic["evidence"] == ["task_1", "task_2"]
    assert [p["evidence"] for p in critic["input"]["packets"]] == ["packet for a", "packet for b"]
    assert ctx.steps == ["DeepResearch._plan", "DeepResearch._write", "DeepResearch._review"]
    assert writer.given[0]["verified"] == [claim(1), claim(2)]
    assert result["verified"] == [claim(1), claim(2)]
    assert result["rejected"] == [] and result["gaps_unresolved"] == []
    assert result["rounds"] == 1 and result["citations_outside_verified"] == []
    assert [d["id"] for d in result["directions"]] == ["d1", "d2"]
    assert [r["handle"] for r in result["researchers"]] == ["task_1", "task_2"]
    assert result["critics"] == [
        {
            "round": 1,
            "handle": "task_3",
            "model": "acct/large",
            "operational_update": False,
            "evidence_review": False,
            "source_auditors": ["task_3"],
            "permission_revision": flow_module._permission_revision(
                {"status": "available", "receipts": []}
            ),
        }
    ]
    assert "## Unresolved questions" not in result["answer"]
    assert result["answer"].startswith("# Report")


def test_a_named_gap_gets_exactly_one_targeted_round() -> None:
    audits = [
        audit([claim(1)], gaps=[gap("who ruled?")]),
        audit([claim(1), claim(2)], resolved=["who ruled?"]),
    ]
    ctx = ScriptedCtx(Children(audits))

    result = run(make_flow(Planner(["a", "b"])), ctx)

    researchers = of(ctx, "researcher")
    assert [r["key"] for r in researchers] == ["research:d1", "research:d2", "research:g2.1"]
    assert researchers[2]["input"]["direction"]["question"] == "who ruled?"
    assert researchers[2]["input"]["round"] == 2
    first, second = of(ctx, "critic")
    assert second["key"] == "verify:2"
    # The second critic reads only the new packet, with the first audit pinned and carried.
    assert second["evidence"] == ["task_4", "task_3", "fetch_1"]
    assert [p["id"] for p in second["input"]["packets"]] == ["g2.1"]
    assert second["input"]["earlier_audit"]["verified"] == [claim(1)]
    assert second["input"]["earlier_audit"]["gaps"] == [gap("who ruled?")]
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
    assert writer.given[0]["delivery"]["stage"] == "after_synthesis"
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
    assert of(ctx, "critic")[0]["input"]["assignments"][0]["question"] == "Inspect a local report"
    assert result["gaps_unresolved"] == [filesystem, delivery]
    assert result["persistence"]["status"] == "unavailable"

    # A missing declaration is unknown access, not permission to assume web tools.
    ctx = ScriptedCtx(Children([]))
    ctx.resolution.subagents = []
    result = run(make_flow(Planner(["public documentation"])), ctx)
    assert not ctx.calls
    assert result["rounds"] == 0
    assert result["gaps_unresolved"] == [gap("public documentation")]


def test_a_later_critic_sees_deferred_requirements_but_only_web_gaps_are_delegated(
    tmp_path: Path,
) -> None:
    delivery = gap(
        "Verify report persistence",
        closure_kind="workflow_action",
        required_tools=[],
        action="persist_report",
    )
    ctx = ScriptedCtx(
        Children(
            [
                audit([claim(1)], gaps=[delivery, gap("contradiction")]),
                audit([claim(1), claim(2)], gaps=[delivery], resolved=["contradiction"]),
            ]
        ),
        workspace=tmp_path,
    )
    result = run(make_flow(Planner(["a"])), ctx)
    assert [r["input"]["direction"]["question"] for r in of(ctx, "researcher")] == [
        "a",
        "contradiction",
    ]
    assert of(ctx, "critic")[1]["input"]["earlier_audit"]["gaps"] == [
        delivery,
        gap("contradiction"),
    ]
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
        audit([claim(1)], gaps=[gap("when?")], resolved=["who ruled?"]),
    ]
    writer = Writer()
    ctx = ScriptedCtx(Children(audits))

    result = run(make_flow(Planner(["a"]), writer, max_rounds=1), ctx)

    assert len(of(ctx, "critic")) == 2 and result["rounds"] == 2
    assert result["gaps_unresolved"] == [gap("when?")]
    assert writer.given[0]["unresolved_gaps"] == [gap("when?")]
    assert "## Unresolved questions\n\n- when? (it could change the answer)" in result["answer"]


def test_omission_cannot_erase_an_unanswered_requirement_or_a_capped_web_gap() -> None:
    external = gap("Operator input", closure_kind="external_input", required_tools=[])
    pending = [external, gap("selected follow-up"), gap("capped follow-up")]
    ctx = ScriptedCtx(Children([audit([claim(1)], gaps=pending), audit([claim(1)])]))
    result = run(make_flow(Planner(["a"]), max_directions=1, max_rounds=1), ctx)
    assert result["gaps_unresolved"] == pending
    assert [r["input"]["direction"]["question"] for r in of(ctx, "researcher")] == [
        "a",
        "selected follow-up",
    ]
    assert of(ctx, "critic")[1]["input"]["open_requirements"] == pending


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


def test_unrepaired_outside_citations_stall_before_persistence(tmp_path: Path) -> None:
    writer = Writer(extra="\n[a blog](https://unsupported.example/claim)")
    ctx = ScriptedCtx(Children([audit([claim(1)])]), workspace=tmp_path)
    with pytest.raises(FlowStall) as stalled:
        run(make_flow(Planner(["a"]), writer), ctx)
    assert stalled.value.stall == "report_citations_invalid"
    assert stalled.value.details["observed"]["urls"] == ["https://unsupported.example/claim"]
    assert "https://unsupported.example/claim" in stalled.value.details["observed"]["draft"]
    assert len(writer.given) == 2
    assert not any(s.endswith("persist_report") for s in ctx.steps)
    assert not list(tmp_path.rglob("*.md"))


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
def test_max_rounds_bounds_the_gap_rounds(max_rounds: int) -> None:
    audits = [
        audit([claim(1)], gaps=[gap(f"open {n}")], resolved=[f"open {n - 1}"] if n else [])
        for n in range(10)
    ]
    ctx = ScriptedCtx(Children(audits))

    result = run(make_flow(Planner(["a"]), max_rounds=max_rounds), ctx)

    assert len(of(ctx, "critic")) == max_rounds + 1
    assert len(of(ctx, "researcher")) == max_rounds + 1
    assert result["rounds"] == max_rounds + 1
    assert result["gaps_unresolved"] == [gap(f"open {max_rounds}")]


def test_max_directions_caps_the_plan_and_each_gap_round() -> None:
    planner = Planner([f"q{n}" for n in range(1, 6)])
    audits = [audit(gaps=[gap(f"g{n}") for n in range(1, 5)]), audit()]
    ctx = ScriptedCtx(Children(audits))

    result = run(make_flow(planner, max_directions=3, max_rounds=1), ctx)

    assert planner.asked[0]["max_directions"] == 3
    assert [r["key"] for r in of(ctx, "researcher")] == [
        "research:d1",
        "research:d2",
        "research:d3",
        "research:g2.1",
        "research:g2.2",
        "research:g2.3",
    ]
    assert [d["question"] for d in result["directions"]] == ["q1", "q2", "q3"]
    assert of(ctx, "critic")[0]["input"]["max_gaps"] == 3
    assert ctx.events[:2] == [
        {"event": "directions_capped", "round": 0, "asked": 5, "kept": 3, "dropped": ["q4", "q5"]},
        {"event": "gaps_capped", "round": 2, "asked": 4, "kept": 3, "dropped": ["g4"]},
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


def test_an_audit_off_schema_is_restated_once_then_stalls() -> None:
    bad = {"answer": "audit", "workflow_state": {"audit": {"verified": [{"claim": "x"}]}}}
    ctx = ScriptedCtx(Children([bad, audit([claim(1)])]))

    result = run(make_flow(Planner(["a"])), ctx)

    first, repair = of(ctx, "critic")
    assert repair["key"] == "verify:1:repair" and repair["evidence"] == ["task_2"]
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


def test_unresolved_semantic_fault_stops_before_persistence(tmp_path: Path) -> None:
    issue = {
        "owner": "report",
        "excerpt": "unsupported connective",
        "reason": "The report is still stronger than its mapped claims",
        "claim_ids": [],
    }
    ctx = ScriptedCtx(Children([audit([claim(1)])]), workspace=tmp_path)
    with pytest.raises(FlowStall) as stalled:
        run(make_flow(Planner(["a"]), reviewer=Reviewer([[issue], [issue]])), ctx)
    assert stalled.value.stall == "report_review_unresolved"
    assert len(stalled.value.details["observed"]["reviews"]) == 2
    assert not list(tmp_path.rglob("*.md"))


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


def test_a_failed_researcher_reaches_the_critic_and_all_failing_ends_the_run() -> None:
    ctx = ScriptedCtx(Children([audit(gaps=[gap("b again")])], fail={"b"}))
    result = run(make_flow(Planner(["a", "b"]), max_rounds=0), ctx)
    packets = of(ctx, "critic")[0]["input"]["packets"]
    assert packets[1]["failed"]["reason"] == "call_failed" and "evidence" not in packets[1]
    assert of(ctx, "critic")[0]["evidence"] == ["task_1"]
    assert result["researchers"][1]["failed"]["reason"] == "call_failed"

    ctx = ScriptedCtx(Children([], fail={"a", "b"}))
    with pytest.raises(GatherFailed):
        run(make_flow(Planner(["a", "b"])), ctx)
    assert of(ctx, "critic") == []

    # A gap round whose researchers all fail still reaches the critic.
    audits = [audit([claim(1)], gaps=[gap("b")]), audit([claim(1)], gaps=[gap("b")])]
    ctx = ScriptedCtx(Children(audits, fail={"b"}))
    result = run(make_flow(Planner(["a"]), max_rounds=1), ctx)
    assert of(ctx, "critic")[1]["input"]["packets"][0]["failed"]["reason"] == "call_failed"
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
        ({"max_directions": 0}, "max_directions must be between 1 and 12"),
        ({"concurrency": -1}, "concurrency must be between 0 and 12"),
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
