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
    """Known parent report actions, deferred until the document exists."""
    return gap.closure_kind == "workflow_action" and gap.action in {
        "review_report",
        "persist_report",
    }


def action_receipts(
    document: str, reviews: list[dict[str, Any]], persistence: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Bind each parent-stage outcome to the exact document it inspected."""
    digest = hashlib.sha256(document.encode("utf-8")).hexdigest()
    review = reviews[-1] if reviews else {}
    accepted = review.get("status") == "accepted_by_reviewer"
    matches = review.get("report_sha256") == digest
    saved = (
        persistence.get("status") == "verified"
        and persistence.get("text_sha256") == digest
        and persistence.get("readback_text_sha256") == digest
    )
    return {
        "review_report": {
            "status": "accepted_by_reviewer" if accepted and matches else "unverified",
            "report_sha256": digest,
            "review": review,
            "verification": "model_judgment_of_exact_draft",
        },
        "persist_report": {**persistence, "status": "verified" if saved else "unverified"},
    }


def action_completed(gap: dict[str, Any], receipts: dict[str, dict[str, Any]]) -> bool:
    """Settle only the registered requirement whose own receipt establishes closure."""
    expected = {"review_report": "accepted_by_reviewer", "persist_report": "verified"}
    action = gap["action"]
    return action in expected and receipts.get(action, {}).get("status") == expected[action]


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


def without_unverified_links(text: str, urls: list[str]) -> str:
    """Turn links to sources outside the verified evidence into marked plain text.

    The report may cite only verified sources. A link the writer added anyway keeps
    its words, loses its target, and says so; nothing unchecked reads as a citation.
    """
    for url in urls:
        target = re.escape(url) + r"[/.,;:]*"
        text = re.sub(r"\[([^\]]*)\]\(<?" + target + r">?\)", r"\1 (unverified source)", text)
        text = re.sub(target, "(unverified source)", text)
    return text


def with_open_issues(document: str, issues: list[dict[str, Any]]) -> str:
    """Append the reviewer's remaining objections, so the reader sees them."""
    if not issues:
        return document
    lines = [
        "## Open review notes",
        "",
        "An independent reviewer still raised these points on the final draft. Read the "
        "passages they name with care.",
        "",
    ]
    for issue in issues:
        excerpt = " ".join(str(issue.get("excerpt") or "").split())
        excerpt = excerpt if len(excerpt) <= 200 else excerpt[:199] + "…"
        lines.append(f"- “{excerpt}”: {' '.join(str(issue.get('reason') or '').split())}")
    return document.rstrip() + "\n\n" + "\n".join(lines) + "\n"


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
        across: list[dict[str, Any]],
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
                across,
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
                report = render_report(typed, audit.verified, audit._papers)
            except (ValidationError, ValueError) as exc:
                issues.append(
                    ReviewIssue(owner="report", excerpt=str(blocks), reason=str(exc)).model_dump()
                )
            # Only the writer's own prose can cite outside the evidence: the citations
            # and References the flow renders come from verified claims, and a fetched
            # page's title can itself contain a URL (a funding note, 2026-11-14).
            prose = "\n\n".join(str(row.get("text") or "") for row in blocks)
            outside = cited_outside(prose, verified) if report else []
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
                # The writer had its correction. Deliver the report rather than lose
                # the research: links outside the verified evidence lose their target,
                # and the reviewer's remaining objections are printed with the report.
                report = without_unverified_links(report, outside)
                document = without_unverified_links(with_open_issues(document, issues), outside)
                verdict["status"] = "delivered_with_open_issues"
                verdict["report_sha256"] = hashlib.sha256(document.encode()).hexdigest()
                await self.ctx.record_event(
                    {
                        "event": "report_delivered_with_open_issues",
                        "attempt": attempt + 1,
                        "issues": issues,
                        "unverified_urls": outside,
                    }
                )
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
            if any(issue["owner"] == "audit" for issue in issues):
                if not critics:
                    raise FlowStall(
                        "report_review_unresolved",
                        "evidence review needs an actual source audit",
                        step="report",
                        observed={"draft": report, "reviews": reviews},
                    )
                # The disputed claims, against the pinned sources: not the whole round again.
                audit, critic = await self.flow._verify(
                    self.ctx,
                    question,
                    [],
                    [],
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
