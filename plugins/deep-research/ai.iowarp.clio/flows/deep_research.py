"""The ``deep-research`` flow: plan, research and check in parallel, coordinate, report.

The flow encodes the method's shape; every decision in it is a model's:

* the planner (a recorded model step) decides which directions the question needs
  and how many;
* each ``researcher`` subagent decides how to search and what its evidence shows,
  and returns its findings as typed claims, each with a fetched URL and a quote;
* CLIO checks each claim's quote against the page that researcher fetched
  (``quote_gate``), a fact about reality, not a judgment;
* one ``critic`` subagent per researcher, all at once, decides which of that
  researcher's claims are verified and which are rejected, and names the open
  questions it sees, typed in ``workflow_state.audit``;
* the coordinator (a recorded model step) reads every assignment and every
  verified claim, says what the claims show together, and decides whether any
  follow-up research is needed: the one place that sends more researchers;
* the writer (a recorded model step) separates verified external facts from
  supplied context, labelled assumptions and design proposals;
* a separate recorded semantic review challenges the source graph and full report,
  returning faults to the auditor or writer before delivery.

The flow branches only on those typed, schema-validated fields. Its options are
growth bounds (how many directions, follow-up rounds and concurrent researchers),
not decisions. A bound that cuts what a model asked for is recorded as a run event.
"""

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

import dspy
from pydantic import BaseModel

from clio_agent.flows.outcomes import CallCancelled, FlowOutcome, FlowStall, GatherFailed
from clio_agent.sdk import Flow
from clio_agent.sdk.flow import FlowOptionsInvalid

from ..audit import (
    Audit,
    Direction,
    Gap,
)
from ..audit import (
    PermissionRequirement as PermissionRequirement,
)
from ..audit import (
    _audit_of as _audit_of,
)
from ..audit import (
    _permission_covers as _permission_covers,
)
from ..blocked import blocked_message, round_block
from ..coordinate import Coordinate, as_gap, checked_across, verified_digest
from ..evidence import (
    ReportBlock,
    ReviewIssue,
    ReviewReport,
    VerifiedClaim,
    public_sources,
)
from ..evidence import (
    bind_claims as bind_claims,
)
from ..evidence import (
    merge_claims as merge_claims,
)
from ..evidence import (
    source_records as source_records,
)
from ..packet import typed_claims
from ..quote_gate import gate_claims as gate_claims
from ..report import ReportSynthesis, action_completed, action_receipts, delivery_record
from ..report import is_delivery as _is_delivery
from ..verify import (
    DEFAULT_CONCURRENCY_CAP,
    Verification,
    _capabilities,
    _child_label,
    _permission_revision,
    _researchable,
)

#: A runaway backstop on directions (and follow-ups per round), not a target: the
#: planner sizes the run to the question; a cut above it is recorded (``directions_capped``).
DIRECTIONS_BACKSTOP = 20
#: Ceiling on follow-up rounds a caller may ask for (``checked_options`` refuses more).
MAX_ROUNDS_CEILING = 5


class PlanResearch(dspy.Signature):
    """Plan the research a question needs as independent directions.

    Each direction is one precise question, with the work needed to answer it,
    why it matters and what would answer it (source families, data,
    period, jurisdiction). Cover the material subquestions, competing explanations,
    stakeholder views, time-sensitive facts and the primary sources the question
    turns on. Use the capability inventory, not imagined access. Label work that
    cannot be answered from web sources with its actual closure_kind; it will not
    be sent to a web researcher. Report persistence belongs to the registered
    persist_report action after synthesis; review_report reviews the completed draft.
    These parent stages are never web research questions. Distinguish
    a requested design or proposed benchmark from an instruction to execute it:
    unprovided measurements and approvals may be conditional design inputs, not
    new requirements. Directions must not overlap.

    Size the plan to the question, not to a number: one direction for a simple
    question, about three for a typical one, more only for genuinely independent
    parts, most important first. Prefer fewer, more capable researchers over many
    narrow ones; a follow-up round can still add what the first one misses. When
    max_directions is set, stay within it. Each researcher reads only its own
    direction, so write each as a self-contained question with no unexplained
    acronyms, and say in answer_looks_like what it does not cover when a
    neighbouring direction does. Give each direction a short name that tells it
    apart from the others.
    Operational evidence supplies this assignment's exact scope IDs. Never invent
    an authorization blocker merely because a tool might later ask permission.
    A concrete permission input must use a supplied scope/permission ID.
    """

    question: str = dspy.InputField()
    max_directions: int | None = dspy.InputField(
        desc="A limit the person set; none means size the plan to the question"
    )
    capabilities: dict[str, Any] = dspy.InputField(
        desc="Declared researcher tools and flow actions"
    )
    operational_evidence: dict[str, Any] = dspy.InputField(
        desc="Own scope IDs and attributable permission history"
    )
    format_problem: str = dspy.InputField(
        desc="Empty, or why your previous reply could not be read; return every field in its declared shape"
    )
    directions: list[Direction] = dspy.OutputField()


class WriteReport(dspy.Signature):
    """Write the research report with explicit evidence and assumption boundaries.

    Lead with the answer or assessment, then the evidence and reasoning in the
    clearest structure for the question: a title, the question and its scope, a
    short executive answer, findings, then a conclusion and `References`.

    Every externally sourced factual sentence rests on verified claims and cites each claim's
    evidence source URLs; a paragraph
    with several sourced claims needs enough citations to make the mapping
    unambiguous. Use no external fact, figure, date or source that is not in the verified
    claims, not even one you know. The person's supplied context is usable when
    identified as supplied, not independently verified. Label calculations from
    those inputs, assumptions, design proposals and proposed acceptance criteria.
    A benchmark design is not a benchmark execution or a measured ranking.
    Keep units, populations, periods and the dates
    sources give attached to figures. Label your own synthesis, inferences and
    scenarios as such, separate from sourced facts, and say where verified claims
    disagree. ``across`` holds what the verified claims show together:
    corroborations, contradictions and joint inferences, each with the claim IDs it
    rests on. Use it for the disagreements and the conclusion; a joint inference is
    synthesis, so label it as such and map it to every claim it rests on.

    operational_evidence is attributable permission history, separate from web
    source evidence. Initial timeouts remain failed attempts after a later grant.
    A historical grant is not a claim of present authority or successful execution.
    Conversely, an unresolved operational gap must not negate current verified
    source claims: explain the specific time and scope of the uncertainty.
    Missing attributed receipts do not prove that no approval occurred.

    Return Markdown blocks, each with text, kind and claim_ids. Map every sourced
    assertion to all supporting atomic claims; split a paragraph if that makes its
    provenance clearer. Source citations and References are rendered by the flow
    from those IDs, so do not hand-write citations or a References section.
    Use kind=structure only for headings or transitions, never to hide factual
    assertions. Label proposals, supplied context, calculations and inferences
    clearly in the prose as well as the map. Every independently checkable clause
    needs its own supporting claim; do not merge facts while losing a document.

    Where an unresolved gap limits a finding, say so at that finding. The flow
    appends the unresolved questions and the rejected claims after your report, so
    do not list them again. Do not cite a search page or an unverified source.

    The report is where the verified evidence reaches the person: each part of the
    question that verified claims answer gets its findings, with those claims. When
    previous_blocks holds an earlier draft, the reply is still the complete report:
    keep each block no issue concerns, and correct, add or remove only what the
    issues and citation problems require.

    Delivery is handled by the flow after synthesis using the supplied delivery
    contract. Do not claim this document has or has not been saved, inspected or
    read back: those actions have not happened yet. Their actual outcome is
    returned separately as the flow's persistence receipt.
    """

    question: str = dspy.InputField()
    verified: list[VerifiedClaim] = dspy.InputField(desc="The claims the critic verified")
    across: list[dict[str, Any]] = dspy.InputField(
        desc="What the verified claims show together, each finding with its claim IDs"
    )
    unresolved_gaps: list[Gap] = dspy.InputField(desc="Material questions still open")
    delivery: dict[str, Any] = dspy.InputField(desc="Parent-owned post-synthesis delivery contract")
    operational_evidence: dict[str, Any] = dspy.InputField(
        desc="Scoped historical permission receipts"
    )
    citation_problems: list[str] = dspy.InputField(
        desc="An earlier draft cited these unverified URLs; write a corrected report using verified sources"
    )
    review_feedback: list[ReviewIssue] = dspy.InputField(
        desc="Concrete issues in the earlier draft to correct"
    )
    previous_blocks: list[dict[str, Any]] = dspy.InputField(
        desc="The complete earlier draft, empty for the first attempt; the reply replaces it whole"
    )
    blocks: list[ReportBlock] = dspy.OutputField(
        desc="Complete report in readable Markdown units with an evidence map"
    )


class DeepResearch(Flow):
    """Plan directions, research and check them in parallel, coordinate follow-ups, report.

    Options: ``max_directions`` (a limit on the directions the planner may plan and
    the follow-ups one round researches; unset, the planner sizes the run),
    ``max_rounds`` (follow-up rounds after the first research round; default 1, 0
    researches once), ``concurrency`` (researchers, and verifiers, at once; 0 runs
    a round together, up to 6), ``researcher_model`` and ``critic_model`` (the model
    each subagent runs on; empty lets it choose). The planner, the coordinator and
    the writer run on this run's model. The final semantic reviewer also uses the
    run's model and a separate signature.
    """

    id = "deep-research"
    description = (
        "Deep web research with independent verification: plans research directions, "
        "researches them in parallel, checks each researcher's quotes against the pages "
        "it fetched, has one independent critic per researcher verify its claims, then "
        "a coordinator reasons across the verified evidence and decides any follow-up "
        "research. Writes a Markdown report separating verified facts, supplied context "
        "and proposals, with open questions and rejected claims listed. A separate "
        "semantic review checks the evidence map and full report before delivery, with "
        "one correction allowed. The planner sizes the run to the question. "
        "Options: max_directions (only to limit it), "
        "max_rounds (follow-up rounds, default 1, at most 5), concurrency (researchers "
        "at once; 0 runs a round together), researcher_model and critic_model. The "
        "planner, coordinator, writer and final reviewer run on the run's model."
    )
    shape = """railroad-beta
deep_research = sequence(terminal("plan"),
                         oneOrMore(sequence(
                             choice(sequence(terminal("researcher 1"), terminal("check 1")),
                                    sequence(terminal("researcher n"), terminal("check n"))),
                             terminal("coordinate")), "follow-ups"),
                         terminal("draft"), terminal("review"),
                         optional(sequence(choice(terminal("audit correction"), terminal("draft correction")), terminal("review"))),
                         terminal("deliver"));"""
    max_directions: int = 0  # 0: no limit set; the planner sizes the run
    max_rounds: int = 1
    concurrency: int = 0
    researcher_model: str = ""
    critic_model: str = ""

    def __init__(self, ref: str | None = None, **options: Any) -> None:
        super().__init__(ref, **options)
        self.planner = dspy.ChainOfThought(PlanResearch)
        self.coordinator = dspy.ChainOfThought(Coordinate)
        self.writer = dspy.Predict(WriteReport)
        self.reviewer = dspy.Predict(ReviewReport)

    @property
    def _limit(self) -> int:
        """The person's limit on directions and gaps per round, else the backstop."""
        return self.max_directions or DIRECTIONS_BACKSTOP

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
    def _plan(
        self,
        question: str,
        max_directions: int,
        capabilities: dict[str, Any],
        operational_evidence: dict[str, Any],
        format_problem: str = "",
    ) -> dict[str, Any]:
        try:
            prediction = self.planner(
                question=question,
                max_directions=max_directions or None,
                capabilities=capabilities,
                operational_evidence=operational_evidence,
                format_problem=format_problem,
            )
            return {
                "directions": [_as_model(Direction, d).model_dump() for d in prediction.directions]
            }
        except Exception as exc:  # noqa: BLE001 - recorded; one format correction, then typed
            return {"failed": _failure(exc)}

    def _write(
        self,
        question: str,
        verified: list[dict[str, Any]],
        gaps: list[dict[str, Any]],
        delivery: dict[str, Any],
        operational_evidence: dict[str, Any],
        citation_problems: list[str] | None = None,
        review_feedback: list[dict[str, Any]] | None = None,
        previous_blocks: list[dict[str, Any]] | None = None,
        across: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        try:
            prediction = self.writer(
                question=question,
                verified=[VerifiedClaim.model_validate(row) for row in verified],
                across=across or [],
                unresolved_gaps=[Gap.model_validate(row) for row in gaps],
                delivery=delivery,
                operational_evidence=operational_evidence,
                citation_problems=citation_problems or [],
                review_feedback=[ReviewIssue.model_validate(row) for row in review_feedback or []],
                previous_blocks=previous_blocks or [],
            )
        except Exception as exc:  # noqa: BLE001 - recorded by the synthesis; research kept
            return {"failed": _failure(exc)}
        return {
            "blocks": [
                row.model_dump() if isinstance(row, BaseModel) else row for row in prediction.blocks
            ]
        }

    def _review(
        self,
        question: str,
        verified: list[dict[str, Any]],
        sources: list[dict[str, Any]],
        operational_evidence: dict[str, Any],
        gaps: list[dict[str, Any]],
        rejected: list[dict[str, Any]],
        blocks: list[dict[str, Any]],
        report: str,
        format_problem: str = "",
    ) -> dict[str, Any]:
        try:
            prediction = self.reviewer(
                question=question,
                verified=[VerifiedClaim.model_validate(row) for row in verified],
                source_records=sources,
                operational_evidence=operational_evidence,
                unresolved_gaps=gaps,
                rejected_claims=rejected,
                blocks=[ReportBlock.model_validate(row) for row in blocks],
                report=report,
                format_problem=format_problem,
            )
        except Exception as exc:  # noqa: BLE001 - recorded by the synthesis; research kept
            return {"failed": _failure(exc)}
        return {
            "issues": [ReviewIssue.model_validate(row).model_dump() for row in prediction.issues]
        }

    def _coordinate(
        self,
        question: str,
        plan: list[dict[str, Any]],
        assignments: list[dict[str, Any]],
        verified: list[dict[str, Any]],
        proposed_gaps: list[dict[str, Any]],
        researcher_tools: list[str],
        rounds_left: int,
        max_follow_ups: int,
        format_problem: str = "",
    ) -> dict[str, Any]:
        try:
            prediction = self.coordinator(
                question=question,
                plan=plan,
                assignments=assignments,
                verified=verified,
                proposed_gaps=[Gap.model_validate(row) for row in proposed_gaps],
                researcher_tools=researcher_tools,
                rounds_left=rounds_left,
                max_follow_ups=max_follow_ups or None,
                format_problem=format_problem,
            )
        except Exception as exc:  # noqa: BLE001 - recorded: the run keeps its evidence
            # No decision was made, so none is invented: nothing more is researched and
            # the verifiers' proposals stay open. The flow records why.
            return {"failed": _failure(exc)}
        return {
            field: [
                row.model_dump() if isinstance(row, BaseModel) else row
                for row in getattr(prediction, field) or []
            ]
            for field in ("across", "follow_ups", "open_questions")
        }

    # ------------------------------------------------------------------ run
    async def forward(self, task: Any, ctx: Any) -> Any:
        question = task if isinstance(task, str) else json.dumps(task, sort_keys=True)
        capabilities = _capabilities(ctx)
        planning_evidence = await ctx.permission_receipts()
        plan = await ctx.step(
            self._plan, question, self.max_directions, capabilities, planning_evidence
        )
        if plan.get("failed"):
            # One format correction, told what could not be read; then a typed stop.
            await ctx.record_event({"event": "planner_reply_unreadable", "reason": plan["failed"]})
            plan = await ctx.step(
                self._plan,
                question,
                self.max_directions,
                capabilities,
                planning_evidence,
                plan["failed"],
            )
            if plan.get("failed"):
                raise FlowStall(
                    "planner_unreadable",
                    "the planner's reply could not be read, twice",
                    step="plan",
                    observed=plan,
                )
        planned = list(plan.get("directions") or [])
        if not planned:
            raise FlowStall(
                "planner_no_directions",
                "the planner returned no research directions",
                step="plan",
                observed=plan,
            )
        kept = await _bounded(ctx, planned, self._limit, "directions_capped", 0)
        directions = [{"id": f"d{n}", **row} for n, row in enumerate(kept, 1)]

        targets = _researchable(directions, capabilities)
        deferred = [row for row in directions if row not in targets]
        audit = Audit(gaps=[Gap.model_validate(row) for row in deferred])
        critics: list[dict[str, Any]] = []
        researched: list[dict[str, Any]] = []
        assignments: list[dict[str, Any]] = []
        resolutions: list[dict[str, Any]] = []
        decision: dict[str, Any] | None = None
        unresearched: list[dict[str, Any]] = []
        rounds = 0
        while targets:
            rounds += 1
            before = await ctx.permission_receipts(refresh=True)
            packets = await self._research(ctx, question, targets, rounds)
            researched += packets
            tools = await self._tool_rows(ctx, packets)
            after = await ctx.permission_receipts(refresh=True)
            block = round_block([row for rows in tools.values() for row in rows], before, after)
            if block:
                await ctx.record_event({"event": "research_blocked", "round": rounds, **block})
                if rounds == 1:
                    # Nothing could be searched: stop with the reason, never re-research.
                    raise FlowStall(
                        "research_blocked", blocked_message(block), step="research", observed=block
                    )
                # Deliver what was verified; the follow-ups stay open questions.
                unresearched = [as_gap(target) for target in targets]
                break
            # One checkpointed snapshot for the round's critics, taken before they start.
            operational = await ctx.permission_receipts()
            audit, checks, outcomes = await Verification(self).check_round(
                ctx, question, targets, packets, tools, audit, rounds, operational
            )
            critics += checks
            resolutions += [{"round": rounds, **row.model_dump()} for row in audit.resolved_gaps]
            assignments += [
                {
                    key: target[key]
                    for key in ("id", "name", "question", "differs_from")
                    if target.get(key)
                }
                | {"round": rounds, "outcome": outcomes[target["id"]]}
                for target in targets
            ]
            rounds_left = max(0, self.max_rounds + 1 - rounds)
            if rounds_left and any(gap.input_kind == "permission" for gap in audit.gaps):
                # Research waits on the person's permission: more rounds can't close it.
                await ctx.record_event({"event": "gap_rounds_stopped", "reason": "permission"})
                rounds_left = 0
            decision, follow_ups = await self._coordinated(
                ctx, question, directions, assignments, audit, capabilities, rounds, rounds_left
            )
            targets = [{"id": f"g{rounds + 1}.{n}", **row} for n, row in enumerate(follow_ups, 1)]
        if decision is not None:
            # The coordinator saw every proposed question: its open questions replace
            # the verifiers' researchable proposals; other requirements stay as typed.
            researchable = {
                row["gap_id"]
                for row in _researchable([gap.model_dump() for gap in audit.gaps], capabilities)
            }
            kept = [gap for gap in audit.gaps if gap.gap_id not in researchable]
            opened = [
                Gap.model_validate(as_gap(row))
                for row in [*decision["open_questions"], *unresearched]
            ]
            audit.gaps = list({gap.gap_id: gap for gap in [*kept, *opened]}.values())

        operational_evidence = await ctx.permission_receipts(refresh=True)
        if (
            critics
            and any(gap.input_kind == "permission" for gap in audit.gaps)
            and critics[-1]["permission_revision"] != _permission_revision(operational_evidence)
        ):
            audit, critic = await self._verify(
                ctx,
                question,
                [],
                [],
                (audit, critics[-1]),
                rounds,
                operational_update=operational_evidence,
            )
            critics.append(critic)
            resolutions += [{"round": rounds, **row.model_dump()} for row in audit.resolved_gaps]

        across = decision["across"] if decision is not None else []
        synthesis = await ReportSynthesis(self, ctx, _record).run(
            question,
            audit,
            across,
            critics,
            resolutions,
            rounds,
            operational_evidence,
            capabilities["workflow_actions"],
        )
        audit = synthesis["audit"]
        operational_evidence = synthesis["operational_evidence"]
        verified = [claim.model_dump() for claim in audit.verified]
        rejected = [claim.model_dump() for claim in audit.rejected]
        delivery_gaps = [gap.model_dump() for gap in audit.gaps if _is_delivery(gap)]
        unresolved = [gap.model_dump() for gap in audit.gaps if not _is_delivery(gap)]
        for gap in unresolved:
            if gap["closure_kind"] == "web_research":
                missing = sorted(set(gap["required_tools"]) - set(capabilities["researcher_tools"]))
                if missing:
                    await ctx.record_event(
                        {
                            "event": "gap_capability_unavailable",
                            "gap": gap,
                            "missing_tools": missing,
                        }
                    )
        document = synthesis["document"]
        if ctx.workspace.root is not None:
            name = _report_name(question, ctx.run_id)
            workspace = ctx.workspace

            def persist_report(name: str, text: str) -> dict[str, Any]:
                return _persist_report(workspace, name, text)

            persistence = await ctx.step(persist_report, name, document)
        else:
            persistence = {"status": "unavailable", "reason": "no_workspace", "path": ""}
            await ctx.record_event({"event": "report_not_written", "reason": "no_workspace"})
        await ctx.record_event({"event": "report_persistence", **persistence})
        receipts = action_receipts(document, synthesis["reviews"], persistence)
        unresolved += [gap for gap in delivery_gaps if not action_completed(gap, receipts)]
        report_path = persistence["path"] if persistence["status"] == "verified" else ""
        typed = {
            "delivery": delivery_record(
                audit, synthesis["blocks"], synthesis["reviews"], persistence, unresolved
            ),
            "report_path": report_path,
            "persistence": persistence,
            "delivery_requirements": delivery_gaps,
            "action_receipts": receipts,
            "capabilities": capabilities,
            "operational_evidence": operational_evidence,
            "sources": public_sources(audit._sources),
            "report_blocks": synthesis["blocks"],
            "report_reviews": synthesis["reviews"],
            "directions": directions,
            "verified": verified,
            "rejected": rejected,
            "gaps_unresolved": unresolved,
            "gap_resolutions": resolutions,
            "across": across,
            "assignments": assignments,
            "rounds": rounds,
            "citations_outside_verified": synthesis["outside"],
            "rejected_draft_citations": synthesis["draft_citations"],
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
                label=_child_label(target),
            )
            for target in targets
        ]
        # Each packet is read from its own result: researchers' sections are not merged.
        results = await ctx.gather(calls, limit=limit, return_exceptions=True, merge_state=False)
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
                claims, invalid = typed_claims(result)
                if claims:
                    row["claims"] = claims
                if invalid:
                    await ctx.record_event(
                        {
                            "event": "packet_claims_invalid",
                            "direction": target["id"],
                            "dropped": invalid,
                        }
                    )
            packets.append(row)
        return packets

    async def _tool_rows(
        self, ctx: Any, packets: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Each researcher's pinned tool results, read once per round, by its handle."""

        return {
            packet["handle"]: await ctx.tool_results(packet["handle"])
            for packet in packets
            if packet.get("handle")
        }

    async def _verify(self, ctx: Any, *args: Any, **kwargs: Any) -> tuple[Audit, dict[str, Any]]:
        """A critic's audit of the whole ledger (see :meth:`Verification.verify`)."""
        return await Verification(self).verify(ctx, *args, **kwargs)

    async def _coordinated(
        self,
        ctx: Any,
        question: str,
        directions: list[dict[str, Any]],
        assignments: list[dict[str, Any]],
        audit: Audit,
        capabilities: dict[str, Any],
        round_no: int,
        rounds_left: int,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """The coordinator's decision, checked against reality, and the follow-ups to run.

        ``across`` keeps only findings resting on verified claims. Follow-ups need a
        round left, the researcher's declared tools and room under the bound; one
        that cannot run stays an open question. Every cut is a recorded event.
        """

        plan = [
            {key: row[key] for key in ("id", "name", "question") if row.get(key)}
            for row in directions
        ]
        inputs = (
            question,
            plan,
            assignments,
            verified_digest(audit),
            [gap.model_dump() for gap in audit.gaps],
            capabilities["researcher_tools"],
            rounds_left,
            self.max_directions,
        )
        decision = await ctx.step(self._coordinate, *inputs)
        if decision.get("failed"):
            # One format correction, told what could not be read.
            await ctx.record_event(
                {
                    "event": "coordinator_reply_unreadable",
                    "round": round_no,
                    "reason": decision["failed"],
                }
            )
            decision = await ctx.step(self._coordinate, *inputs, decision["failed"])
        if decision.get("failed"):
            await ctx.record_event(
                {"event": "coordinator_failed", "round": round_no, "reason": decision["failed"]}
            )
            proposals = _researchable([gap.model_dump() for gap in audit.gaps], capabilities)
            return {"across": [], "open_questions": proposals}, []
        across, cut = checked_across(
            decision.get("across") or [], {claim.claim_id for claim in audit.verified}
        )
        if cut:
            await ctx.record_event(
                {"event": "across_unverified_claims", "round": round_no, "cut": cut}
            )
        follow_ups = list(decision.get("follow_ups") or [])
        opened = list(decision.get("open_questions") or [])
        if follow_ups and not rounds_left:
            await ctx.record_event(
                {
                    "event": "follow_ups_after_last_round",
                    "round": round_no,
                    "questions": [row["question"] for row in follow_ups],
                }
            )
            opened += follow_ups
            follow_ups = []
        runnable = _researchable(follow_ups, capabilities)
        if len(runnable) < len(follow_ups):
            other = [row for row in follow_ups if row not in runnable]
            await ctx.record_event(
                {
                    "event": "follow_ups_not_researchable",
                    "round": round_no,
                    "questions": [row["question"] for row in other],
                }
            )
            opened += other
        chosen = await _bounded(ctx, runnable, self._limit, "follow_ups_capped", round_no + 1)
        opened += runnable[len(chosen) :]
        await ctx.record_event(
            {
                "event": "coordinated",
                "round": round_no,
                "rounds_left": rounds_left,
                "across": len(across),
                "follow_ups": [row["question"] for row in chosen],
                "open_questions": len(opened),
                "input_characters": len(json.dumps(inputs, default=str)),
            }
        )
        return {"across": across, "open_questions": opened}, chosen


_OPTIONS = ("max_directions", "max_rounds", "concurrency", "researcher_model", "critic_model")
#: The integer options and the range each may take.
_BOUNDS = {
    "max_directions": (0, DIRECTIONS_BACKSTOP),
    "max_rounds": (0, MAX_ROUNDS_CEILING),
    "concurrency": (0, DIRECTIONS_BACKSTOP),
}


def _failure(exc: Exception) -> str:
    """Why a model step's reply could not be used, kept short for the run record.

    A parse failure's own message starts with the whole reply; the validation
    problems that say what was wrong come last, so the end is what is kept.
    """
    text = str(exc)
    if hasattr(exc, "lm_response"):
        # A parse failure: keep the field and its validation errors, not the whole
        # value and model reply that the message repeats around them.
        text = text.split("\n\nAdapter ", 1)[0]
        text = re.sub(r" with value .* from the LM response\.", ".", text, flags=re.S)
    text = f"{type(exc).__name__}: {text}"
    return text if len(text) <= 1600 else text[:400] + " … " + text[-1200:]


def _persist_report(workspace: Any, name: str, text: str) -> dict[str, Any]:
    """One journalled parent action: write and verify logical UTF-8 report text."""
    path = ""
    try:
        path = workspace.write(name, text)
        observed = workspace.read(name)
    except (OSError, UnicodeError, ValueError) as exc:
        return {"status": "failed", "path": path, "reason": type(exc).__name__, "detail": str(exc)}
    expected_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    observed_hash = hashlib.sha256(observed.encode("utf-8")).hexdigest()
    return {
        "status": "verified" if observed == text else "failed",
        "path": path,
        "reason": "" if observed == text else "readback_mismatch",
        "verification": "workspace_text_readback",
        "text_sha256": expected_hash,
        "readback_text_sha256": observed_hash,
        "characters": len(text),
    }


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


def _report_name(question: str, run_id: str) -> str:
    """The report's workspace path: the question's first words and the run."""

    slug = re.sub(r"[^a-z0-9]+", "-", question.lower()).strip("-")[:48].strip("-")
    return f"deep-research/{slug or 'report'}-{run_id[-8:]}.md"


def _record(unresolved: list[dict[str, Any]], rejected: list[dict[str, Any]]) -> str:
    """The verification record appended to the report, from the critic's typed audit."""

    parts: list[str] = []
    closures = {
        "web_research": "Further source research",
        "workflow_action": "Workflow action",
        "external_input": "Input needed",
        "unavailable_action": "Unavailable execution",
        "design_limit": "Design boundary",
    }
    if unresolved:
        parts.append(
            "## Unresolved questions\n\n"
            + "\n".join(
                f"- {g['question']}"
                + (f" ({g['why']})" if g["why"] else "")
                + f" — {closures[g['closure_kind']]}"
                + (f"; requires: {', '.join(g['required_tools'])}" if g["required_tools"] else "")
                + (f"; action: {g['action']}" if g["action"] else "")
                + (f". Closure: {g['answer_looks_like']}" if g["answer_looks_like"] else "")
                for g in unresolved
            )
        )
    if rejected:
        parts.append(
            "## Rejected claims\n\nThe critic did not verify these; they are not findings.\n\n"
            + "\n".join(f"- {c['claim']}: {c['reason']}" for c in rejected)
        )
    return "".join(f"\n\n{part}" for part in parts)
