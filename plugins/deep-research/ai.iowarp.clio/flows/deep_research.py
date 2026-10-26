"""The ``deep-research`` flow: plan, research in parallel, verify, close gaps, report.

The flow encodes the method's shape; every decision in it is a model's:

* the planner (a recorded model step) decides which directions the question needs
  and how many;
* each ``researcher`` subagent decides how to search and what its evidence shows;
* the ``critic`` subagent decides which claims are verified, which are rejected and
  which gaps remain, and returns them typed in ``workflow_state.audit``;
* the writer (a recorded model step) separates verified external facts from
  supplied context, labelled assumptions and design proposals;
* a separate recorded semantic review challenges the source graph and full report,
  returning faults to the auditor or writer before delivery.

The flow branches only on those typed, schema-validated fields. Its options are
growth bounds (how many directions, gap rounds and concurrent researchers), not
decisions. A bound that cuts what a model asked for is recorded as a run event.
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
    _audit_of,
    repair_context,
)
from ..audit import (
    PermissionRequirement as PermissionRequirement,
)
from ..audit import (
    _permission_covers as _permission_covers,
)
from ..evidence import (
    ReportBlock,
    ReviewIssue,
    ReviewReport,
    VerifiedClaim,
    bind_claims,
    public_sources,
    source_records,
)
from ..evidence import (
    merge_claims as merge_claims,
)
from ..report import ReportSynthesis, action_completed, action_receipts, delivery_record
from ..report import is_delivery as _is_delivery

#: Ceilings on what a caller may ask for in one run (``checked_options`` refuses more).
MAX_DIRECTIONS_CEILING = 12
MAX_ROUNDS_CEILING = 5
#: Researchers running at once when the caller sets no ``concurrency``.
DEFAULT_CONCURRENCY_CAP = 8


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
    new requirements. Directions must not overlap. Plan as many as the question needs, never
    more than max_directions, most important first; a narrow question may need one.
    Operational evidence supplies this assignment's exact scope IDs. Never invent
    an authorization blocker merely because a tool might later ask permission.
    A concrete permission input must use a supplied scope/permission ID.
    """

    question: str = dspy.InputField()
    max_directions: int = dspy.InputField(desc="The most directions you may plan")
    capabilities: dict[str, Any] = dspy.InputField(
        desc="Declared researcher tools and flow actions"
    )
    operational_evidence: dict[str, Any] = dspy.InputField(
        desc="Own scope IDs and attributable permission history"
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
    disagree.

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

    Delivery is handled by the flow after synthesis using the supplied delivery
    contract. Do not claim this document has or has not been saved, inspected or
    read back: those actions have not happened yet. Their actual outcome is
    returned separately as the flow's persistence receipt.
    """

    question: str = dspy.InputField()
    verified: list[VerifiedClaim] = dspy.InputField(desc="The claims the critic verified")
    unresolved_gaps: list[Gap] = dspy.InputField(desc="Material questions still open")
    delivery: dict[str, Any] = dspy.InputField(desc="Parent-owned post-synthesis delivery contract")
    operational_evidence: dict[str, Any] = dspy.InputField(
        desc="Scoped historical permission receipts"
    )
    citation_problems: list[str] = dspy.InputField(
        desc="An earlier draft cited these unverified URLs; write a corrected report using verified sources"
    )
    review_feedback: list[ReviewIssue] = dspy.InputField(
        desc="Concrete issues in a previous draft to correct"
    )
    previous_blocks: list[dict[str, Any]] = dspy.InputField(
        desc="Earlier draft, empty for the first attempt"
    )
    blocks: list[ReportBlock] = dspy.OutputField(
        desc="Complete report in readable Markdown units with an evidence map"
    )


class DeepResearch(Flow):
    """Plan directions, research them in parallel, verify independently, close gaps, report.

    Options: ``max_directions`` (the most directions the planner may plan, and the
    most gaps one round researches; default 6), ``max_rounds`` (gap-closing rounds
    after the first research round; default 2, 0 verifies once), ``concurrency``
    (researchers at once; 0 runs all of a round together, up to 8),
    ``researcher_model`` and ``critic_model`` (the model each subagent runs on;
    empty lets it choose). The planner and the writer run on this run's model.
    The final semantic reviewer also uses the run's model and a separate signature.
    """

    id = "deep-research"
    description = (
        "Deep web research with independent verification: plans research directions, "
        "researches them in parallel, has an independent critic verify sourced claims "
        "against fetched sources and name the gaps, researches those gaps, then writes "
        "a Markdown report separating verified facts, supplied context and proposals, with open questions "
        "and rejected claims listed. A separate semantic review checks the evidence map and full report "
        "before delivery, with one correction allowed. Options: max_directions (default 6, at most 12), "
        "max_rounds (gap-closing rounds, default 2, at most 5), concurrency (researchers "
        "at once; 0 runs a round together), researcher_model and critic_model. The "
        "planner, writer and final reviewer run on the run's model."
    )
    shape = """railroad-beta
deep_research = sequence(terminal("plan"),
                         choice(terminal("researcher 1"), terminal("researcher n")),
                         terminal("critic"),
                         optional(oneOrMore(sequence(
                             choice(terminal("gap researcher 1"), terminal("gap researcher n")),
                             terminal("critic")))),
                         terminal("draft"), terminal("review"),
                         optional(sequence(choice(terminal("audit correction"), terminal("draft correction")), terminal("review"))),
                         terminal("deliver"));"""
    max_directions: int = 6
    max_rounds: int = 2
    concurrency: int = 0
    researcher_model: str = ""
    critic_model: str = ""

    def __init__(self, ref: str | None = None, **options: Any) -> None:
        super().__init__(ref, **options)
        self.planner = dspy.ChainOfThought(PlanResearch)
        self.writer = dspy.Predict(WriteReport)
        self.reviewer = dspy.Predict(ReviewReport)

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
    ) -> dict[str, Any]:
        prediction = self.planner(
            question=question,
            max_directions=max_directions,
            capabilities=capabilities,
            operational_evidence=operational_evidence,
        )
        return {"directions": [_as_model(Direction, d).model_dump() for d in prediction.directions]}

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
    ) -> dict[str, Any]:
        prediction = self.writer(
            question=question,
            verified=[VerifiedClaim.model_validate(row) for row in verified],
            unresolved_gaps=[Gap.model_validate(row) for row in gaps],
            delivery=delivery,
            operational_evidence=operational_evidence,
            citation_problems=citation_problems or [],
            review_feedback=[ReviewIssue.model_validate(row) for row in review_feedback or []],
            previous_blocks=previous_blocks or [],
        )
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
    ) -> dict[str, Any]:
        prediction = self.reviewer(
            question=question,
            verified=[VerifiedClaim.model_validate(row) for row in verified],
            source_records=sources,
            operational_evidence=operational_evidence,
            unresolved_gaps=gaps,
            rejected_claims=rejected,
            blocks=[ReportBlock.model_validate(row) for row in blocks],
            report=report,
        )
        return {
            "issues": [ReviewIssue.model_validate(row).model_dump() for row in prediction.issues]
        }

    # ------------------------------------------------------------------ run
    async def forward(self, task: Any, ctx: Any) -> Any:
        question = task if isinstance(task, str) else json.dumps(task, sort_keys=True)
        capabilities = _capabilities(ctx)
        planning_evidence = await ctx.permission_receipts()
        plan = await ctx.step(
            self._plan, question, self.max_directions, capabilities, planning_evidence
        )
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

        targets = _researchable(directions, capabilities)
        deferred = [row for row in directions if row not in targets]
        packets = await self._research(ctx, question, targets, 1) if targets else []
        researched = list(packets)
        if targets:
            audit, critic = await self._verify(ctx, question, directions, packets, None, 1)
            critics = [critic]
        else:
            audit = Audit(gaps=[Gap.model_validate(row) for row in deferred])
            critics = []
        rounds = 1 if targets else 0
        resolutions = [{"round": rounds, **row.model_dump()} for row in audit.resolved_gaps]
        while rounds and rounds - 1 < self.max_rounds:
            gaps = _researchable([gap.model_dump() for gap in audit.gaps], capabilities)
            if not gaps:
                break
            rounds += 1
            chosen = await _bounded(ctx, gaps, self.max_directions, "gaps_capped", rounds)
            targets = [{"id": f"g{rounds}.{n}", **row} for n, row in enumerate(chosen, 1)]
            packets = await self._research(ctx, question, targets, rounds)
            researched += packets
            earlier = (audit, critic)
            audit, critic = await self._verify(ctx, question, targets, packets, earlier, rounds)
            critics.append(critic)
            resolutions += [{"round": rounds, **row.model_dump()} for row in audit.resolved_gaps]

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

        synthesis = await ReportSynthesis(self, ctx, _record).run(
            question,
            audit,
            researched,
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
        operational_update: dict[str, Any] | None = None,
        evidence_review: list[dict[str, Any]] | None = None,
    ) -> tuple[Audit, dict[str, Any]]:
        """The critic's complete audit of this round's evidence, schema-validated."""

        request: dict[str, Any] = {
            "question": question,
            "round": round_no,
            "assignments": targets,
            "packets": [_packet(p) for p in packets],
            "max_gaps": self.max_directions,
            "capabilities": _capabilities(ctx),
            "operational_evidence": operational_update
            if operational_update is not None
            else await ctx.permission_receipts(),
        }
        if operational_update is not None:
            request["operational_update"] = True
        if evidence_review:
            request["evidence_review"] = evidence_review
        evidence = [p["handle"] for p in packets if p.get("handle")]
        pending = [
            Gap.model_validate(row)
            for row in targets
            if row not in _researchable(targets, _capabilities(ctx))
        ]
        if earlier is not None:
            earlier_audit, critic = earlier
            pending = earlier_audit.gaps
            request["earlier_audit"] = {
                "verified": [claim.model_dump() for claim in earlier_audit.verified],
                "rejected": [claim.model_dump() for claim in earlier_audit.rejected],
                "gaps": [gap.model_dump() for gap in earlier_audit.gaps],
            }
            evidence.append(critic["handle"])
            evidence += list(earlier_audit._sources)
            request["source_inventory"] = public_sources(earlier_audit._sources)
        request["open_requirements"] = [gap.model_dump() for gap in pending]
        stage = f"verify:{round_no}" + (":permissions" if operational_update is not None else "")
        if evidence_review:
            stage += ":evidence"
        result = await ctx.call(
            "critic",
            request,
            evidence=evidence,
            key=stage,
            model=self.critic_model,
        )
        prior_audit = earlier[0] if earlier is not None else None
        auditors = {result.handle}
        rows = await ctx.tool_results(result.handle)
        records = dict(prior_audit._sources) if prior_audit is not None else {}
        records.update(source_records(rows, auditors))
        audit, problems = _audit_of(result, pending, prior_audit, request["operational_evidence"])
        if audit is not None:
            problems += bind_claims(audit.verified, records)
        if audit is None or problems:
            await ctx.record_event(
                {
                    "event": "critic_audit_repair",
                    "round": round_no,
                    "critic": result.handle,
                    "problems": problems,
                    "source_count": len(records),
                }
            )
            prior_audit, continuity = repair_context(
                result.workflow_state.get("audit"),
                pending,
                prior_audit,
                records,
                request["operational_evidence"],
            )
            pending = list({gap.gap_id: gap for gap in [*pending, *prior_audit.gaps]}.values())
            await ctx.record_event(
                {"event": "critic_audit_continuity", "round": round_no, **continuity}
            )
            result = await ctx.call(
                "critic",
                {
                    "question": question,
                    "round": round_no,
                    "repair": problems,
                    "audit_as_returned": result.workflow_state.get("audit"),
                    "validated_prior_ledger": prior_audit.model_dump(),
                    "capabilities": _capabilities(ctx),
                    "open_requirements": [gap.model_dump() for gap in prior_audit.gaps],
                    "operational_evidence": request["operational_evidence"],
                    "operational_update": operational_update is not None,
                    "source_inventory": public_sources(records),
                    "evidence_review": evidence_review or [],
                },
                evidence=[result.handle, *records],
                key=f"{stage}:repair",
                model=self.critic_model,
            )
            audit, problems = _audit_of(
                result,
                pending,
                prior_audit,
                request["operational_evidence"],
                carry_resolutions=True,
            )
            auditors.add(result.handle)
            for auditor in sorted(auditors):
                rows = await ctx.tool_results(auditor)
                records.update(source_records(rows, auditors))
            if audit is not None:
                problems += bind_claims(audit.verified, records)
        if audit is None or problems:
            raise FlowStall(
                "critic_audit_invalid",
                f"the critic's audit for round {round_no} does not match its schema",
                step=f"verify:{round_no}",
                observed=problems,
                handle=result.handle,
            )
        audit._sources = records
        return audit, {
            "round": round_no,
            "handle": result.handle,
            "model": result.model,
            "permission_revision": _permission_revision(request["operational_evidence"]),
            "operational_update": operational_update is not None,
            "evidence_review": bool(evidence_review),
            "source_auditors": sorted(auditors),
        }


_OPTIONS = ("max_directions", "max_rounds", "concurrency", "researcher_model", "critic_model")
#: The integer options and the range each may take.
_BOUNDS = {
    "max_directions": (1, MAX_DIRECTIONS_CEILING),
    "max_rounds": (0, MAX_ROUNDS_CEILING),
    "concurrency": (0, MAX_DIRECTIONS_CEILING),
}


def _capabilities(ctx: Any) -> dict[str, Any]:
    """Read the installed researcher's allowlist; never invent missing tool access."""
    rows = getattr(getattr(ctx, "resolution", None), "subagents", ())
    researcher: dict[str, Any] = next((row for row in rows if row.get("id") == "researcher"), {})
    tools = researcher.get("tools")
    return {
        "researcher_tools": sorted(tools) if isinstance(tools, list) else [],
        "workflow_actions": {
            "review_report": {
                "stage": "after_draft",
                "available": True,
                "verification": "recorded model judgment of exact draft against source passages and operational history; not proof of truth",
            },
            "persist_report": {
                "stage": "after_synthesis",
                "available": ctx.workspace.root is not None,
                "verification": "write then read back the complete report text",
            },
        },
    }


def _researchable(rows: list[dict[str, Any]], capabilities: dict[str, Any]) -> list[dict[str, Any]]:
    """Dispatch only model-classified web work supported by the declared tools."""
    available = set(capabilities["researcher_tools"])
    return [
        row
        for row in rows
        if row["closure_kind"] == "web_research"
        and row["required_tools"]
        and set(row["required_tools"]) <= available
    ]


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


def _permission_revision(evidence: dict[str, Any]) -> str:
    """Identify the exact historical permission evidence an audit consumed."""
    return hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()


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
