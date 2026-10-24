"""The deep-research flow on a scripted ``ctx``: method shape, bounds, typed audit, replay.

The ``ctx`` here implements the surface the flow uses (``call``, ``gather``, ``step``,
``record_event``) the way CLIO's runtime does: a call's identity is fixed when it is
made, a gather runs at most ``limit`` calls at once and hands back typed outcomes with
``return_exceptions``, and a step returns its recorded result on replay. Results are
``clio_agent.flows.values.CallResult`` objects, as the runtime returns them.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import dspy
import pytest

from clio_agent.flows.outcomes import CallFailed, FlowOutcome, FlowStall, GatherFailed
from clio_agent.flows.values import CallResult, FlowWorkspace
from clio_agent.sdk.flow import FlowOptionsInvalid

PLUGIN = Path(__file__).resolve().parents[1]
FLOW_FILE = PLUGIN / "ai.iowarp.clio" / "flows" / "deep_research.py"
PROMPT = PLUGIN / "ai.iowarp.clio" / "prompt"


def _load_flow_module() -> Any:
    name = "deep_research_flow_under_test"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, FLOW_FILE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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


# ----------------------------------------------------------------- the models
class Planner:
    """Stands in for the planner module: returns the directions it is given."""

    def __init__(self, questions: list[str]) -> None:
        self.questions = questions
        self.asked: list[dict[str, Any]] = []

    def __call__(self, *, question: str, max_directions: int) -> Any:
        self.asked.append({"question": question, "max_directions": max_directions})
        return dspy.Prediction(
            directions=[
                flow_module.Direction(question=q, why=f"why {q}", answer_looks_like="sources")
                for q in self.questions
            ]
        )


class Writer:
    """Stands in for the writer module: cites every verified claim it was given."""

    def __init__(self, extra: str = "") -> None:
        self.extra = extra
        self.given: list[dict[str, Any]] = []

    def __call__(self, *, question: str, verified: list[Any], unresolved_gaps: list[Any]) -> Any:
        self.given.append(
            {
                "question": question,
                "verified": [c.model_dump() for c in verified],
                "unresolved_gaps": [g.model_dump() for g in unresolved_gaps],
            }
        )
        lines = [f"- {c.claim} ([source]({c.source_url}))" for c in verified]
        return dspy.Prediction(report="# Report\n\n" + "\n".join(lines) + self.extra)


def claim(n: int) -> dict[str, str]:
    return {
        "claim": f"claim {n}",
        "source_url": f"https://example.org/{n}",
        "quote": f"passage {n}",
        "source_title": f"Source {n}",
    }


def gap(text: str) -> dict[str, str]:
    return {"question": text, "why": "it could change the answer", "answer_looks_like": "a filing"}


def audit(verified: list[Any] = (), rejected: list[Any] = (), gaps: list[Any] = ()) -> dict:
    return {
        "answer": "audit summary",
        "workflow_state": {
            "audit": {"verified": list(verified), "rejected": list(rejected), "gaps": list(gaps)}
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


def make_flow(planner: Planner, writer: Writer | None = None, **options: Any) -> Any:
    flow = DeepResearch()
    for key, value in DeepResearch.checked_options(options).items():
        setattr(flow, key, value)
    flow.planner = planner
    flow.writer = writer or Writer()
    return flow


def run(flow: Any, ctx: ScriptedCtx, question: str = "What changed?") -> dict[str, Any]:
    return asyncio.run(flow.forward(question, ctx))


def of(ctx: ScriptedCtx, target: str) -> list[dict[str, Any]]:
    return [row for row in ctx.calls if row["target"] == target]


# --------------------------------------------------------------------- tests
def test_plan_research_verify_report() -> None:
    planner, writer = Planner(["a", "b"]), Writer()
    ctx = ScriptedCtx(Children([audit([claim(1), claim(2)])]))
    flow = make_flow(planner, writer, researcher_model="acct/small", critic_model="acct/large")

    result = run(flow, ctx)

    assert planner.asked == [{"question": "What changed?", "max_directions": 6}]
    researchers = of(ctx, "researcher")
    assert [r["key"] for r in researchers] == ["research:d1", "research:d2"]
    assert [r["input"]["direction"]["question"] for r in researchers] == ["a", "b"]
    assert {r["model"] for r in researchers} == {"acct/small"}
    (critic,) = of(ctx, "critic")
    assert critic["key"] == "verify:1" and critic["model"] == "acct/large"
    assert critic["evidence"] == ["task_1", "task_2"]
    assert [p["evidence"] for p in critic["input"]["packets"]] == ["packet for a", "packet for b"]
    assert ctx.steps == ["DeepResearch._plan", "DeepResearch._write"]
    assert writer.given[0]["verified"] == [claim(1), claim(2)]
    assert result["verified"] == [claim(1), claim(2)]
    assert result["rejected"] == [] and result["gaps_unresolved"] == []
    assert result["rounds"] == 1 and result["citations_outside_verified"] == []
    assert [d["id"] for d in result["directions"]] == ["d1", "d2"]
    assert [r["handle"] for r in result["researchers"]] == ["task_1", "task_2"]
    assert result["critics"] == [{"round": 1, "handle": "task_3", "model": "acct/large"}]
    assert "## Unresolved questions" not in result["answer"]
    assert result["answer"].startswith("# Report")


def test_a_named_gap_gets_exactly_one_targeted_round() -> None:
    audits = [audit([claim(1)], gaps=[gap("who ruled?")]), audit([claim(1), claim(2)])]
    ctx = ScriptedCtx(Children(audits))

    result = run(make_flow(Planner(["a", "b"])), ctx)

    researchers = of(ctx, "researcher")
    assert [r["key"] for r in researchers] == ["research:d1", "research:d2", "research:g2.1"]
    assert researchers[2]["input"]["direction"]["question"] == "who ruled?"
    assert researchers[2]["input"]["round"] == 2
    first, second = of(ctx, "critic")
    assert second["key"] == "verify:2"
    # The second critic reads only the new packet, with the first audit pinned and carried.
    assert second["evidence"] == ["task_4", "task_3"]
    assert [p["id"] for p in second["input"]["packets"]] == ["g2.1"]
    assert second["input"]["earlier_audit"]["verified"] == [claim(1)]
    assert second["input"]["earlier_audit"]["gaps"] == [gap("who ruled?")]
    assert result["rounds"] == 2 and result["gaps_unresolved"] == []
    assert result["verified"] == [claim(1), claim(2)]


def test_a_gap_left_open_at_the_bound_is_reported_unresolved() -> None:
    audits = [audit([claim(1)], gaps=[gap("who ruled?")]), audit([claim(1)], gaps=[gap("when?")])]
    writer = Writer()
    ctx = ScriptedCtx(Children(audits))

    result = run(make_flow(Planner(["a"]), writer, max_rounds=1), ctx)

    assert len(of(ctx, "critic")) == 2 and result["rounds"] == 2
    assert result["gaps_unresolved"] == [gap("when?")]
    assert writer.given[0]["unresolved_gaps"] == [gap("when?")]
    assert "## Unresolved questions\n\n- when? (it could change the answer)" in result["answer"]


@pytest.mark.parametrize("max_rounds", [0, 1, 2, 3])
def test_max_rounds_bounds_the_gap_rounds(max_rounds: int) -> None:
    audits = [audit([claim(1)], gaps=[gap(f"open {n}")]) for n in range(10)]
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

    result = run(make_flow(planner, max_directions=3), ctx)

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
    writer = Writer(extra="\n\nSee also [a blog](https://blog.example.net/post).")
    ctx = ScriptedCtx(Children([audit([claim(1)], rejected=[rejected])]))

    result = run(make_flow(Planner(["a"]), writer), ctx)

    given = json.dumps(writer.given)
    assert "the moon is cheese" not in given
    assert writer.given[0]["verified"] == [claim(1)]
    report, record = result["answer"].split("## Rejected claims", 1)
    assert "the moon is cheese" not in report
    assert "- the moon is cheese: no source supports it" in record
    assert result["rejected"] == [rejected]
    # A citation outside the verified sources is surfaced, not removed.
    assert result["citations_outside_verified"] == ["https://blog.example.net/post"]
    assert {
        "event": "report_cites_unverified_source",
        "urls": ["https://blog.example.net/post"],
    } in (ctx.events)
    assert "## Citations outside the verified sources" in result["answer"]


def test_the_report_is_written_to_the_workspace_and_typed_for_the_caller(tmp_path: Path) -> None:
    ctx = ScriptedCtx(Children([audit([claim(1)], gaps=[gap("open")])]), workspace=tmp_path)

    result = run(make_flow(Planner(["a"]), max_rounds=0), ctx, "Why did the rule change?")

    path = Path(result["report_path"])
    assert path == tmp_path / "deep-research" / "why-did-the-rule-change-89abcdef.md"
    assert path.read_text(encoding="utf-8") == result["answer"]
    assert ctx.steps[-1] == "FlowWorkspace.write"
    typed = result["workflow_state"]["deep_research"]
    assert typed["report_path"] == str(path) and typed["verified"] == [claim(1)]
    assert typed["gaps_unresolved"] == [gap("open")] and typed["rounds"] == 1

    ctx = ScriptedCtx(Children([audit([claim(1)])]))
    assert run(make_flow(Planner(["a"])), ctx)["report_path"] == ""
    assert {"event": "report_not_written", "reason": "no_workspace"} in ctx.events


def test_replay_reattaches_to_the_same_calls_and_steps() -> None:
    def fresh() -> Children:
        return Children([audit([claim(1)], gaps=[gap("open")]), audit([claim(1), claim(2)])])

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
    assert any("source_url" in problem for problem in repair["input"]["repair"])
    assert result["verified"] == [claim(1)]

    ctx = ScriptedCtx(Children([bad, {"answer": "still prose"}]))
    with pytest.raises(FlowStall) as stalled:
        run(make_flow(Planner(["a"])), ctx)
    assert stalled.value.stall == "critic_audit_invalid"


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
