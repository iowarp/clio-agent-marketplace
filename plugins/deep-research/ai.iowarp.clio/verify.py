"""Checking research: one critic per researcher, and the critic's audit settled.

A round's researchers are checked at once, each by its own critic that reads
only that researcher's direction and packet (claims bound by the quote gate,
with the page text around each quote). Each audit is validated against its
schema and its quotes bound to actual fetches, with one repair before a typed
stall, and the round's audits are merged into the ledger. The same critic call
and settlement serve the whole-ledger reviews (a permission update and the
final evidence review).
"""

import hashlib
import json
from typing import Any

from clio_agent.flows.outcomes import CallCancelled, FlowOutcome, FlowStall
from clio_agent.flows.values import render_input

from .audit import Audit, Gap, _audit_of, exclude_unbound, merge_shards, repair_context
from .evidence import bind_claims, paper_records, public_sources, source_records
from .quote_gate import gate_claims, gate_counts, gate_rejections

#: Researchers (and their critics) running at once when the caller sets no ``concurrency``.
DEFAULT_CONCURRENCY_CAP = 6


class Verification:
    """The critic calls of one deep-research run, on the flow's critic model."""

    def __init__(self, flow: Any) -> None:
        self.flow = flow

    async def check_round(
        self,
        ctx: Any,
        question: str,
        targets: list[dict[str, Any]],
        packets: list[dict[str, Any]],
        tools: dict[str, list[dict[str, Any]]],
        prior: Audit,
        round_no: int,
        operational: dict[str, Any],
    ) -> tuple[Audit, list[dict[str, Any]], dict[str, dict[str, Any]]]:
        """One verifier per researcher, all at once; their audits merged over ``prior``.

        Each verifier sees only its researcher's direction and packet. A typed claim
        reaches it bound to the page the researcher fetched (with the text around its
        quote) or unchecked with the gate's reason. A failed researcher gets no
        verifier: the coordinator sees its outcome. A verifier that fails leaves its
        researcher's claims unverified and is recorded; the others' audits stand.
        """

        outcomes: dict[str, dict[str, Any]] = {}
        jobs: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
        unchecked: dict[str, list[dict[str, Any]]] = {}
        for target, packet in zip(targets, packets, strict=True):
            if packet.get("failed"):
                outcomes[target["id"]] = {"failed": packet["failed"]["reason"]}
                continue
            rows = tools.get(packet["handle"], [])
            records = source_records(rows, {packet["handle"]})
            sent = {key: value for key, value in packet.items() if key != "claims"}
            if target.get("name"):
                sent["name"] = target["name"]
            if "claims" in packet:
                gated = gate_claims(packet["claims"], records)
                # The critic reads the bound claims as the packet's claims.
                sent.update(
                    {
                        "claims" if key == "bound" else key: found
                        for key, found in gated.items()
                        if found
                    }
                )
                unchecked[target["id"]] = gated["unchecked"]
                await ctx.record_event(
                    {
                        "event": "claims_gated",
                        "round": round_no,
                        "direction": target["id"],
                        **gate_counts(gated),
                    }
                )
            shard = {
                "id": target["id"],
                "label": "Check: " + _child_label(target),
                # The researcher's fetches bind, and so do the ledger's sources.
                "records": {**prior._sources, **records},
                "papers": paper_records(rows),
            }
            jobs.append((target, sent, shard))
        calls = []
        for target, sent, shard in jobs:
            calls.append(
                await self.critic_call(
                    ctx,
                    question,
                    [target],
                    [sent],
                    None,
                    round_no,
                    operational=operational,
                    shard=shard,
                )
            )
        limit = self.flow.concurrency or min(len(calls), DEFAULT_CONCURRENCY_CAP)
        results = (
            await ctx.gather(
                [call for call, _ in calls],
                limit=limit,
                return_exceptions=True,
                merge_state=False,  # each critic's audit is read from its own result
            )
            if calls
            else []
        )
        shards: list[Audit] = []
        checks: list[dict[str, Any]] = []
        failures: list[FlowOutcome] = []
        for (target, _, _), (_, asked), result in zip(jobs, calls, results, strict=True):
            if isinstance(result, CallCancelled):
                raise result
            if not isinstance(result, FlowOutcome):
                try:
                    result = await self.settle(ctx, question, result, asked)
                except CallCancelled:
                    raise
                except FlowOutcome as outcome:
                    result = outcome
            if isinstance(result, FlowOutcome):
                reason = str(getattr(result, "stall", "") or getattr(result, "reason", ""))
                outcomes[target["id"]] = {"check_failed": reason or type(result).__name__}
                failures.append(result)
                await ctx.record_event(
                    {
                        "event": "check_failed",
                        "round": round_no,
                        "direction": target["id"],
                        "reason": outcomes[target["id"]]["check_failed"],
                        "message": str(result),
                    }
                )
                continue
            shard_audit, record = result
            shards.append(shard_audit)
            checks.append(record)
            outcomes[target["id"]] = {
                "verified": len(shard_audit.verified),
                "rejected": len(shard_audit.rejected),
            }
        if jobs and not shards:
            raise failures[0]  # no verifier finished: nothing this round can be stated
        audit = merge_shards(shards, prior)
        verified = {claim.claim for claim in audit.verified}
        known = {(row.claim, row.source_url) for row in audit.rejected}
        for direction, rows in unchecked.items():
            if "verified" not in outcomes[direction]:
                continue
            for rejection in gate_rejections(rows, verified):
                if (rejection.claim, rejection.source_url) not in known:
                    known.add((rejection.claim, rejection.source_url))
                    audit.rejected.append(rejection)
                    outcomes[direction]["rejected"] += 1
        return audit, checks, outcomes

    async def verify(
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
        """A critic's complete audit of the whole ledger: a permission update or the
        final evidence review."""

        call, asked = await self.critic_call(
            ctx, question, targets, packets, earlier, round_no, operational_update, evidence_review
        )
        return await self.settle(ctx, question, await call, asked)

    async def critic_call(
        self,
        ctx: Any,
        question: str,
        targets: list[dict[str, Any]],
        packets: list[dict[str, Any]],
        earlier: tuple[Audit, dict[str, Any]] | None,
        round_no: int,
        operational_update: dict[str, Any] | None = None,
        evidence_review: list[dict[str, Any]] | None = None,
        *,
        operational: dict[str, Any] | None = None,
        shard: dict[str, Any] | None = None,
    ) -> tuple[Any, dict[str, Any]]:
        """A critic call (not yet awaited) and what :meth:`_settle` needs to read it.

        With ``shard`` it checks one researcher's packet: that researcher's fetches
        (``shard["records"]``) bind as evidence alongside the critic's own, under its
        own key and label.
        """

        if operational_update is not None:
            operational = operational_update
        elif operational is None:
            operational = await ctx.permission_receipts()
        request: dict[str, Any] = {
            "question": question,
            "round": round_no,
            "assignments": targets,
            "packets": [_packet(p) for p in packets],
            "capabilities": _capabilities(ctx),
            "operational_evidence": operational,
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
            evidence += [handle for handle in earlier_audit._sources if handle not in evidence]
            request["source_inventory"] = public_sources(earlier_audit._sources)
        request["open_requirements"] = [gap.model_dump() for gap in pending]
        stage = f"verify:{round_no}" + (f":{shard['id']}" if shard else "")
        stage += ":permissions" if operational_update is not None else ""
        if evidence_review:
            stage += ":evidence"
        label = shard["label"] if shard else ""
        call = ctx.call(
            "critic",
            request,
            evidence=evidence,
            key=stage,
            model=self.flow.critic_model,
            label=label,
        )
        asked = {
            "request": request,
            "pending": pending,
            "stage": stage,
            "label": label,
            "earlier": earlier,
            "shard": shard,
            "round": round_no,
            "operational_update": operational_update,
            "evidence_review": evidence_review,
            # The request reaches the critic inline as its assignment text: this is
            # what its model reads first.
            "input_characters": len(render_input(request)),
        }
        return call, asked

    async def settle(
        self, ctx: Any, question: str, result: Any, asked: dict[str, Any]
    ) -> tuple[Audit, dict[str, Any]]:
        """Validate a critic's audit and bind its evidence; one repair, then a typed stall."""

        request, pending, stage, label = (
            asked[k] for k in ("request", "pending", "stage", "label")
        )
        earlier, shard, round_no = asked["earlier"], asked["shard"], asked["round"]
        operational_update, evidence_review = asked["operational_update"], asked["evidence_review"]
        prior_audit = earlier[0] if earlier is not None else None
        repair_characters = 0
        auditors = {result.handle}
        rows = await ctx.tool_results(result.handle)
        records = dict(prior_audit._sources) if prior_audit is not None else {}
        papers = dict(prior_audit._papers) if prior_audit is not None else {}
        if shard:
            records.update(shard["records"])
            papers.update(shard["papers"])
        records.update(source_records(rows, auditors))
        papers.update(paper_records(rows))
        where = {"direction": shard["id"]} if shard else {}
        audit, problems = _audit_of(result, pending, prior_audit, request["operational_evidence"])
        await _record_claim_repairs(ctx, audit, round_no, result.handle)
        if audit is not None:
            problems += bind_claims(audit.verified, records)
        if audit is None or problems:
            await ctx.record_event(
                {
                    "event": "critic_audit_repair",
                    "round": round_no,
                    **where,
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
                {"event": "critic_audit_continuity", "round": round_no, **where, **continuity}
            )
            repair_request = {
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
            }
            repair_characters = len(render_input(repair_request))
            result = await ctx.call(
                "critic",
                repair_request,
                evidence=[result.handle, *records],
                key=f"{stage}:repair",
                model=self.flow.critic_model,
                label=label,
            )
            audit, problems = _audit_of(
                result,
                pending,
                prior_audit,
                request["operational_evidence"],
                carry_resolutions=True,
            )
            await _record_claim_repairs(ctx, audit, round_no, result.handle)
            auditors.add(result.handle)
            for auditor in sorted(auditors):
                rows = await ctx.tool_results(auditor)
                records.update(source_records(rows, auditors))
                papers.update(paper_records(rows))
            if audit is not None and not problems:
                # The critic had its repair; claims whose evidence still does not
                # bind are rejected with their reason rather than stalling the run.
                excluded = exclude_unbound(audit, records, pending, request["operational_evidence"])
                if excluded:
                    await ctx.record_event(
                        {
                            "event": "critic_unbound_claims_rejected",
                            "round": round_no,
                            **where,
                            "critic": result.handle,
                            "excluded": excluded,
                        }
                    )
        if audit is None or problems:
            raise FlowStall(
                "critic_audit_invalid",
                f"the critic's audit for round {round_no} does not match its schema",
                step=stage,
                observed=problems,
                handle=result.handle,
            )
        audit._sources = records
        audit._papers = papers
        return audit, {
            "round": round_no,
            **where,
            "handle": result.handle,
            "model": result.model,
            "permission_revision": _permission_revision(request["operational_evidence"]),
            "operational_update": operational_update is not None,
            "evidence_review": bool(evidence_review),
            "source_auditors": sorted(auditors),
            "input_characters": asked["input_characters"],
            **({"repair_input_characters": repair_characters} if repair_characters else {}),
        }


async def _record_claim_repairs(ctx: Any, audit: Any, round_no: int, critic: str) -> None:
    """Record IDs derived from claims' text and gaps' fields in place of the critic's."""
    if audit is not None and (audit._claim_id_repairs or audit._gap_id_repairs):
        await ctx.record_event(
            {
                "event": "critic_id_repaired",
                "round": round_no,
                "critic": critic,
                "claim_id_repairs": audit._claim_id_repairs,
                "gap_id_repairs": audit._gap_id_repairs,
            }
        )


def _child_label(target: dict[str, Any]) -> str:
    """The name a researcher is shown under: its direction's name, else its question, short."""

    name = " ".join(str(target.get("name") or "").split())
    if name:
        return name
    question = " ".join(str(target.get("question") or "").split())
    if len(question) <= 48:
        return question or target["id"]
    return question[:48].rsplit(" ", 1)[0].rstrip(",;:") + "…"


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


def _packet(row: dict[str, Any]) -> dict[str, Any]:
    """A packet as the critic reads it (handles travel as pinned evidence)."""

    return {key: value for key, value in row.items() if key not in {"handle", "model"}}


def _permission_revision(evidence: dict[str, Any]) -> str:
    """Identify the exact historical permission evidence an audit consumed."""
    return hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()


__all__ = [
    "DEFAULT_CONCURRENCY_CAP",
    "Verification",
    "_capabilities",
    "_child_label",
    "_permission_revision",
    "_researchable",
]
