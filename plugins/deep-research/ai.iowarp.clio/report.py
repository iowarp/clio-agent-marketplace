"""Synthesis, canonical citation rendering and bounded semantic correction."""

import hashlib
import re
from collections.abc import Callable, Mapping
from typing import Any

from pydantic import ValidationError

from clio_agent.flows.outcomes import FlowStall

from .evidence import ReportBlock, ReviewIssue, render_report, review_sources

_CITED_URL = re.compile(r"https?://[^\s)\]>\"'`]+")


def is_delivery(gap: Any) -> bool:
    """The registered parent report action, deferred until after synthesis."""
    return gap.closure_kind == "workflow_action" and gap.action == "persist_report"


def cited_outside(report: str, verified: list[dict[str, Any]]) -> list[str]:
    """URL hygiene only: membership does not establish that a citation supports prose."""
    sources = {edge["source_url"].rstrip("/.,;:") for row in verified for edge in row["evidence"]}
    return list(
        dict.fromkeys(
            url.rstrip("/.,;:")
            for url in _CITED_URL.findall(report)
            if url.rstrip("/.,;:") not in sources
        )
    )


def delivery_record(
    audit: Any,
    blocks: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    persistence: dict[str, Any],
    unresolved: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compact handoff derived from the exact rendered blocks and observed persistence."""
    cited = {claim_id for block in blocks for claim_id in block.get("claim_ids", [])}
    used = list(
        dict.fromkeys(
            edge.source_url
            for claim in audit.verified
            if claim.claim_id in cited
            for edge in claim.evidence
        )
    )
    return {
        "report_path": persistence["path"] if persistence["status"] == "verified" else "",
        "persistence": persistence,
        "used": used,
        "verified_count": len(audit.verified),
        "rejected_count": len(audit.rejected),
        "gaps_unresolved": unresolved,
        "report_review": {key: reviews[-1][key] for key in ("status", "report_sha256")},
    }


class ReportSynthesis:
    """Give model-identified faults to their owner while preserving every attempt."""

    def __init__(
        self,
        flow: Any,
        ctx: Any,
        record: Callable[[list[dict[str, Any]], list[dict[str, Any]]], str],
    ) -> None:
        self.flow = flow
        self.ctx = ctx
        self.record = record

    async def run(
        self,
        question: str,
        audit: Any,
        packets: list[dict[str, Any]],
        critics: list[dict[str, Any]],
        resolutions: list[dict[str, Any]],
        rounds: int,
        operational_evidence: dict[str, Any],
        delivery: dict[str, Any],
    ) -> dict[str, Any]:
        """Review meaning and evidence mapping; a reviewer acceptance is not proof of truth."""
        feedback: list[dict[str, Any]] = []
        blocks: list[dict[str, Any]] = []
        reviews = []
        draft_citations = []
        outside: list[str] = []
        for attempt in range(2):
            verified = [claim.model_dump() for claim in audit.verified]
            gaps = [gap.model_dump() for gap in audit.gaps if not is_delivery(gap)]
            rejected = [claim.model_dump() for claim in audit.rejected]
            written = await self.ctx.step(
                self.flow._write,
                question,
                verified,
                gaps,
                delivery,
                operational_evidence,
                outside,
                feedback,
                blocks,
            )
            blocks = written.get("blocks") or []
            if not blocks or not any(
                isinstance(row, Mapping) and str(row.get("text") or "").strip() for row in blocks
            ):
                raise FlowStall(
                    "report_empty", "the writer returned no report", step="report", observed=written
                )
            report = ""
            issues: list[dict[str, Any]] = []
            try:
                typed = [ReportBlock.model_validate(row) for row in blocks]
                report = render_report(typed, audit.verified)
            except (ValidationError, ValueError) as exc:
                issues.append(
                    ReviewIssue(owner="report", excerpt=str(blocks), reason=str(exc)).model_dump()
                )
            outside = cited_outside(report, verified) if report else []
            document = (report + self.record(gaps, rejected)).replace("\r\n", "\n")
            if outside:
                draft_citations += [url for url in outside if url not in draft_citations]
                await self.ctx.record_event(
                    {"event": "report_cites_unverified_source", "urls": outside}
                )
                issues += [
                    ReviewIssue(
                        owner="report",
                        excerpt=url,
                        reason="URL is outside the verified evidence graph",
                    ).model_dump()
                    for url in outside
                ]
            if not issues:
                review = await self.ctx.step(
                    self.flow._review,
                    question,
                    verified,
                    review_sources(audit.verified, audit._sources),
                    operational_evidence,
                    gaps,
                    rejected,
                    blocks,
                    document,
                )
                issues = [ReviewIssue.model_validate(row).model_dump() for row in review["issues"]]
            verdict = {
                "attempt": attempt + 1,
                "report_sha256": hashlib.sha256(document.encode()).hexdigest(),
                "status": "issues_found" if issues else "accepted_by_reviewer",
                "issues": issues,
            }
            reviews.append(verdict)
            await self.ctx.record_event({"event": "report_review", **verdict})
            if not issues:
                return {
                    "audit": audit,
                    "report": report,
                    "document": document,
                    "blocks": blocks,
                    "reviews": reviews,
                    "draft_citations": draft_citations,
                    "outside": outside,
                    "operational_evidence": operational_evidence,
                }
            if attempt:
                raise FlowStall(
                    "report_citations_invalid" if outside else "report_review_unresolved",
                    "the corrected report still has unresolved evidence or synthesis problems",
                    step="report",
                    observed={
                        "urls": outside,
                        "draft": document,
                        "blocks": blocks,
                        "reviews": reviews,
                    },
                )
            if any(issue["owner"] == "audit" for issue in issues):
                if not critics:
                    raise FlowStall(
                        "report_review_unresolved",
                        "evidence review needs an actual source audit",
                        step="report",
                        observed={"draft": report, "reviews": reviews},
                    )
                audit, critic = await self.flow._verify(
                    self.ctx,
                    question,
                    [],
                    packets,
                    (audit, critics[-1]),
                    rounds,
                    evidence_review=[issue for issue in issues if issue["owner"] == "audit"],
                )
                critics.append(critic)
                resolutions += [
                    {"round": rounds, **row.model_dump()} for row in audit.resolved_gaps
                ]
                operational_evidence = await self.ctx.permission_receipts(refresh=True)
            feedback = issues
        raise RuntimeError("Synthesis must return an accepted review or raise a typed stall")
