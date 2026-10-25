"""The ``deep-research`` flow: plan, research in parallel, verify, close gaps, report.

The flow encodes the method's shape; every decision in it is a model's:

* the planner (a recorded model step) decides which directions the question needs
  and how many;
* each ``researcher`` subagent decides how to search and what its evidence shows;
* the ``critic`` subagent decides which claims are verified, which are rejected and
  which gaps remain, and returns them typed in ``workflow_state.audit``;
* the writer (a recorded model step) writes the report from verified claims only.

The flow branches only on those typed, schema-validated fields. Its options are
growth bounds (how many directions, gap rounds and concurrent researchers), not
decisions. A bound that cuts what a model asked for is recorded as a run event.
"""

import json
import re
from collections.abc import Mapping
from typing import Any

import dspy
from pydantic import BaseModel, Field, ValidationError

from clio_agent.flows.outcomes import CallCancelled, FlowOutcome, FlowStall, GatherFailed
from clio_agent.sdk import Flow
from clio_agent.sdk.flow import FlowOptionsInvalid

#: Ceilings on what a caller may ask for in one run (``checked_options`` refuses more).
MAX_DIRECTIONS_CEILING = 12
MAX_ROUNDS_CEILING = 5
#: Researchers running at once when the caller sets no ``concurrency``.
DEFAULT_CONCURRENCY_CAP = 8

_HTTP_URL = r"^https?://\S+$"
_CITED_URL = re.compile(r"https?://[^\s)\]>\"'`]+")


class Direction(BaseModel):
    """One research direction: a question a web researcher can answer from sources."""

    question: str = Field(min_length=1, description="One precise, self-contained question")
    why: str = Field(default="", description="Why its answer matters to the person's question")
    answer_looks_like: str = Field(
        default="",
        description="What would answer it: source families, data, period or jurisdiction",
    )


class VerifiedClaim(BaseModel):
    """A claim the critic confirmed on a page it fetched itself."""

    claim: str = Field(min_length=1)
    source_url: str = Field(pattern=_HTTP_URL, description="The fetched page that supports it")
    quote: str = Field(min_length=1, description="The supporting passage, quoted from the page")
    source_title: str = ""


class RejectedClaim(BaseModel):
    """A claim the critic would not stand behind, with its reason."""

    claim: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    source_url: str = ""


class Gap(Direction):
    """A material question the evidence leaves open (the shape of a direction)."""


class Audit(BaseModel):
    """The critic's complete audit: ``workflow_state.audit`` of its result."""

    verified: list[VerifiedClaim] = Field(default_factory=list)
    rejected: list[RejectedClaim] = Field(default_factory=list)
    gaps: list[Gap] = Field(default_factory=list)


class PlanResearch(dspy.Signature):
    """Plan the research a question needs as independent directions.

    Each direction is one precise question a web researcher can answer from fetched
    sources, with why it matters and what would answer it (source families, data,
    period, jurisdiction). Cover the material subquestions, competing explanations,
    stakeholder views, time-sensitive facts and the primary sources the question
    turns on. Directions must not overlap. Plan as many as the question needs, never
    more than max_directions, most important first; a narrow question may need one.
    """

    question: str = dspy.InputField()
    max_directions: int = dspy.InputField(desc="The most directions you may plan")
    directions: list[Direction] = dspy.OutputField()


class WriteReport(dspy.Signature):
    """Write the research report in Markdown from the verified claims only.

    Lead with the answer or assessment, then the evidence and reasoning in the
    clearest structure for the question: a title, the question and its scope, a
    short executive answer, findings, then a conclusion and `References`.

    Every factual sentence rests on verified claims and cites each claim's
    source_url as a Markdown link right after the claim it supports; a paragraph
    with several sourced claims needs enough citations to make the mapping
    unambiguous. Use no fact, figure, date or source that is not in the verified
    claims, not even one you know. Keep units, populations, periods and the dates
    sources give attached to figures. Label your own synthesis, inferences and
    scenarios as such, separate from sourced facts, and say where verified claims
    disagree.

    Where an unresolved gap limits a finding, say so at that finding. The flow
    appends the unresolved questions and the rejected claims after your report, so
    do not list them again. `References` lists every source you cited, each as
    `[title](url)`, and nothing you did not cite. Never cite a search page or a URL
    that is not a verified claim's source_url.
    """

    question: str = dspy.InputField()
    verified: list[VerifiedClaim] = dspy.InputField(desc="The claims the critic verified")
    unresolved_gaps: list[Gap] = dspy.InputField(desc="Material questions still open")
    report: str = dspy.OutputField(desc="The complete Markdown report")


class DeepResearch(Flow):
    """Plan directions, research them in parallel, verify independently, close gaps, report.

    Options: ``max_directions`` (the most directions the planner may plan, and the
    most gaps one round researches; default 6), ``max_rounds`` (gap-closing rounds
    after the first research round; default 2, 0 verifies once), ``concurrency``
    (researchers at once; 0 runs all of a round together, up to 8),
    ``researcher_model`` and ``critic_model`` (the model each subagent runs on;
    empty lets it choose). The planner and the writer run on this run's model.
    """

    id = "deep-research"
    description = (
        "Deep web research with independent verification: plans research directions, "
        "researches them in parallel, has an independent critic verify every claim "
        "against fetched sources and name the gaps, researches those gaps, then writes "
        "a Markdown report cited only from verified claims, with unresolved questions "
        "and rejected claims listed. Options: max_directions (default 6, at most 12), "
        "max_rounds (gap-closing rounds, default 2, at most 5), concurrency (researchers "
        "at once; 0 runs a round together), researcher_model and critic_model. The "
        "planner and the writer run on the run's model."
    )
    shape = """railroad-beta
deep_research = sequence(terminal("plan"),
                         choice(terminal("researcher 1"), terminal("researcher n")),
                         terminal("critic"),
                         optional(oneOrMore(sequence(
                             choice(terminal("gap researcher 1"), terminal("gap researcher n")),
                             terminal("critic")))),
                         terminal("report"));"""
    max_directions: int = 6
    max_rounds: int = 2
    concurrency: int = 0
    researcher_model: str = ""
    critic_model: str = ""

    def __init__(self, ref: str | None = None, **options: Any) -> None:
        super().__init__(ref, **options)
        self.planner = dspy.ChainOfThought(PlanResearch)
        self.writer = dspy.Predict(WriteReport)

    @classmethod
    def checked_options(cls, options: Mapping[str, Any] | None) -> dict[str, Any]:
        """The types Flow checks, plus unknown names and the ranges of the bounds."""

        problems = [
            f"{key} is not an option of {cls.id} (options: {', '.join(_OPTIONS)})"
            for key in (options or {})
            if key not in _OPTIONS
        ]
        problems += [
            f"{key} must be int, not {value!r}"
            for key, value in (options or {}).items()
            if key in _BOUNDS and isinstance(value, bool)
        ]
        if problems:
            raise FlowOptionsInvalid(cls.id, problems)
        checked = super().checked_options(options)
        for key, (low, high) in _BOUNDS.items():
            if key in checked and not low <= checked[key] <= high:
                problems.append(f"{key} must be between {low} and {high}, not {checked[key]!r}")
        if problems:
            raise FlowOptionsInvalid(cls.id, problems)
        return checked

    # ------------------------------------------------------------ model steps
    def _plan(self, question: str, max_directions: int) -> dict[str, Any]:
        prediction = self.planner(question=question, max_directions=max_directions)
        return {"directions": [_as_model(Direction, d).model_dump() for d in prediction.directions]}

    def _write(
        self, question: str, verified: list[dict[str, Any]], gaps: list[dict[str, Any]]
    ) -> dict[str, Any]:
        prediction = self.writer(
            question=question,
            verified=[VerifiedClaim.model_validate(row) for row in verified],
            unresolved_gaps=[Gap.model_validate(row) for row in gaps],
        )
        return {"report": str(prediction.report)}

    # ------------------------------------------------------------------ run
    async def forward(self, task: Any, ctx: Any) -> Any:
        question = task if isinstance(task, str) else json.dumps(task, sort_keys=True)
        plan = await ctx.step(self._plan, question, self.max_directions)
        planned = list(plan.get("directions") or [])
        if not planned:
            raise FlowStall(
                "planner_no_directions",
                "the planner returned no research directions",
                step="plan",
                observed=plan,
            )
        kept = await _bounded(ctx, planned, self.max_directions, "directions_capped", 0)
        directions = [{"id": f"d{n}", **row} for n, row in enumerate(kept, 1)]

        packets = await self._research(ctx, question, directions, 1)
        researched = list(packets)
        audit, critic = await self._verify(ctx, question, directions, packets, None, 1)
        critics = [critic]
        rounds = 1
        while audit.gaps and rounds - 1 < self.max_rounds:
            rounds += 1
            gaps = [gap.model_dump() for gap in audit.gaps]
            chosen = await _bounded(ctx, gaps, self.max_directions, "gaps_capped", rounds)
            targets = [{"id": f"g{rounds}.{n}", **row} for n, row in enumerate(chosen, 1)]
            packets = await self._research(ctx, question, targets, rounds)
            researched += packets
            earlier = (audit, critic)
            audit, critic = await self._verify(ctx, question, targets, packets, earlier, rounds)
            critics.append(critic)

        verified = [claim.model_dump() for claim in audit.verified]
        rejected = [claim.model_dump() for claim in audit.rejected]
        unresolved = [gap.model_dump() for gap in audit.gaps]
        written = await ctx.step(self._write, question, verified, unresolved)
        report = str(written.get("report") or "")
        outside = _cited_outside(report, verified)
        if outside:
            await ctx.record_event({"event": "report_cites_unverified_source", "urls": outside})
        document = report + _record(unresolved, rejected, outside)
        report_path = ""
        if ctx.workspace.root is not None:
            name = _report_name(question, ctx.run_id)
            report_path = await ctx.step(ctx.workspace.write, name, document)
        else:
            await ctx.record_event({"event": "report_not_written", "reason": "no_workspace"})
        typed = {
            "report_path": report_path,
            "directions": directions,
            "verified": verified,
            "rejected": rejected,
            "gaps_unresolved": unresolved,
            "rounds": rounds,
            "citations_outside_verified": outside,
            # Who did each part, on which model: the run's audit trail.
            "researchers": [
                {k: row[k] for k in ("id", "handle", "model", "failed") if k in row}
                for row in researched
            ],
            "critics": critics,
        }
        # The run record keeps the typed fields; workflow_state carries them to the caller.
        return {"answer": document, **typed, "workflow_state": {"deep_research": typed}}

    async def _research(
        self, ctx: Any, question: str, targets: list[dict[str, Any]], round_no: int
    ) -> list[dict[str, Any]]:
        """One researcher per target, together; each packet or its typed failure."""

        limit = self.concurrency or min(len(targets), DEFAULT_CONCURRENCY_CAP)
        calls = [
            ctx.call(
                "researcher",
                {"question": question, "direction": target, "round": round_no},
                key=f"research:{target['id']}",
                model=self.researcher_model,
            )
            for target in targets
        ]
        results = await ctx.gather(calls, limit=limit, return_exceptions=True)
        cancelled = next((r for r in results if isinstance(r, CallCancelled)), None)
        if cancelled is not None:
            raise cancelled
        if round_no == 1 and all(isinstance(r, FlowOutcome) for r in results):
            # Nothing to verify: the run ends with every researcher's typed outcome.
            # A later round's failures reach the critic, which keeps the earlier audit.
            raise GatherFailed("every researcher of the first round failed", list(results))
        packets: list[dict[str, Any]] = []
        for target, result in zip(targets, results, strict=True):
            row = {"id": target["id"], "question": target["question"]}
            if isinstance(result, FlowOutcome):
                row["failed"] = {"reason": result.reason, "message": str(result)}
            else:
                row.update(handle=result.handle, model=result.model, evidence=result.response_text)
            packets.append(row)
        return packets

    async def _verify(
        self,
        ctx: Any,
        question: str,
        targets: list[dict[str, Any]],
        packets: list[dict[str, Any]],
        earlier: tuple[Audit, dict[str, Any]] | None,
        round_no: int,
    ) -> tuple[Audit, dict[str, Any]]:
        """The critic's complete audit of this round's evidence, schema-validated."""

        request: dict[str, Any] = {
            "question": question,
            "round": round_no,
            "assignments": targets,
            "packets": [_packet(p) for p in packets],
            "max_gaps": self.max_directions,
        }
        evidence = [p["handle"] for p in packets if p.get("handle")]
        if earlier is not None:
            audit, critic = earlier
            request["earlier_audit"] = {
                "verified": [claim.model_dump() for claim in audit.verified],
                "rejected": [claim.model_dump() for claim in audit.rejected],
                "gaps": [gap.model_dump() for gap in audit.gaps],
            }
            evidence.append(critic["handle"])
        result = await ctx.call(
            "critic",
            request,
            evidence=evidence,
            key=f"verify:{round_no}",
            model=self.critic_model,
        )
        audit, problems = _audit_of(result)
        if audit is None:
            # Format-only correction: the critic restates its own audit in the schema.
            result = await ctx.call(
                "critic",
                {
                    "question": question,
                    "round": round_no,
                    "repair": problems,
                    "audit_as_returned": result.workflow_state.get("audit"),
                },
                evidence=[result.handle],
                key=f"verify:{round_no}:repair",
                model=self.critic_model,
            )
            audit, problems = _audit_of(result)
        if audit is None:
            raise FlowStall(
                "critic_audit_invalid",
                f"the critic's audit for round {round_no} does not match its schema",
                step=f"verify:{round_no}",
                observed=problems,
                handle=result.handle,
            )
        return audit, {"round": round_no, "handle": result.handle, "model": result.model}


_OPTIONS = ("max_directions", "max_rounds", "concurrency", "researcher_model", "critic_model")
#: The integer options and the range each may take.
_BOUNDS = {
    "max_directions": (1, MAX_DIRECTIONS_CEILING),
    "max_rounds": (0, MAX_ROUNDS_CEILING),
    "concurrency": (0, MAX_DIRECTIONS_CEILING),
}


def _packet(row: dict[str, Any]) -> dict[str, Any]:
    """A packet as the critic reads it (handles travel as pinned evidence)."""

    return {key: value for key, value in row.items() if key not in {"handle", "model"}}


def _as_model(model: type[BaseModel], value: Any) -> BaseModel:
    return value if isinstance(value, model) else model.model_validate(value)


async def _bounded(
    ctx: Any, rows: list[dict[str, Any]], bound: int, event: str, round_no: int
) -> list[dict[str, Any]]:
    """The first ``bound`` rows (the model orders them by importance); a cut is recorded."""

    if len(rows) > bound:
        await ctx.record_event(
            {
                "event": event,
                "round": round_no,
                "asked": len(rows),
                "kept": bound,
                "dropped": [row["question"] for row in rows[bound:]],
            }
        )
    return rows[:bound]


def _audit_of(result: Any) -> tuple[Audit | None, list[str]]:
    """The critic's typed audit, or why its ``workflow_state.audit`` is not one."""

    section = result.workflow_state.get("audit")
    if not isinstance(section, Mapping):
        return None, ["workflow_state.audit is missing or not an object"]
    try:
        return Audit.model_validate(section), []
    except ValidationError as exc:
        return None, [
            f"audit.{'.'.join(str(p) for p in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]


def _report_name(question: str, run_id: str) -> str:
    """The report's workspace path: the question's first words and the run."""

    slug = re.sub(r"[^a-z0-9]+", "-", question.lower()).strip("-")[:48].strip("-")
    return f"deep-research/{slug or 'report'}-{run_id[-8:]}.md"


def _url_key(url: str) -> str:
    return url.rstrip("/.,;:")


def _cited_outside(report: str, verified: list[dict[str, Any]]) -> list[str]:
    """URLs the report cites that are no verified claim's source, in first-cited order."""

    sources = {_url_key(row["source_url"]) for row in verified}
    outside: list[str] = []
    for url in _CITED_URL.findall(report):
        key = _url_key(url)
        if key not in sources and key not in outside:
            outside.append(key)
    return outside


def _record(
    unresolved: list[dict[str, Any]], rejected: list[dict[str, Any]], outside: list[str]
) -> str:
    """The verification record appended to the report, from the critic's typed audit."""

    parts: list[str] = []
    if unresolved:
        parts.append(
            "## Unresolved questions\n\n"
            + "\n".join(
                f"- {g['question']}" + (f" ({g['why']})" if g["why"] else "") for g in unresolved
            )
        )
    if rejected:
        parts.append(
            "## Rejected claims\n\nThe critic did not verify these; they are not findings.\n\n"
            + "\n".join(f"- {c['claim']}: {c['reason']}" for c in rejected)
        )
    if outside:
        parts.append(
            "## Citations outside the verified sources\n\n"
            + "\n".join(f"- {url}" for url in outside)
        )
    return "".join(f"\n\n{part}" for part in parts)
