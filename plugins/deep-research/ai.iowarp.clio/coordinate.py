"""The coordinator: reasons across verified evidence and decides any follow-up research.

Verifiers check each researcher's claims on their own; none of them sees the
whole picture. After each research round one recorded model step does: it reads
every assignment so far with its outcome and every verified claim, says what the
claims show together (corroborations, contradictions, inferences that follow
jointly), and decides which follow-up directions, if any, the answer still needs.
No follow-ups means the research is done. It is the one place that decides more
research, so it can see what was already assigned and not send a researcher after
the same question twice. Its last ``across`` reaches the writer.

The flow only checks the step's output against reality: an ``across`` finding must
rest on verified claim IDs, and follow-ups need a round left and the researcher's
declared tools. Anything that fails is recorded with its reason, never dropped
silently.
"""

from __future__ import annotations

from typing import Any, Literal

import dspy
from pydantic import BaseModel, Field

from .audit import Direction, Gap


class CrossFinding(BaseModel):
    """What several verified claims show together."""

    kind: Literal["corroboration", "contradiction", "inference"]
    statement: str = Field(
        min_length=1, description="What the claims show together, stated plainly"
    )
    claim_ids: list[str] = Field(
        default_factory=list, description="The verified claim IDs this rests on, all of them"
    )


class FollowUp(Direction):
    """A new research direction, with the earlier assignment it is not repeating."""

    differs_from: str = Field(
        default="",
        description="The earlier assignment closest to this one and what this one asks that it did not",
    )


class Coordinate(dspy.Signature):
    """Reason across the verified evidence, then decide whether the answer needs more research.

    First, read the verified claims together. Name what they show only jointly:
    claims from independent sources that corroborate each other, claims that
    contradict each other (say which way the better evidence points, if it does),
    and inferences that follow from several claims but no single source states.
    Cite every claim ID each finding rests on. Do not restate single claims.

    Then decide follow-up research. A follow-up is worth a researcher only when its
    answer could change, qualify or substantially strengthen the answer to the
    person's question: an explicit part of the question no assignment answered, a
    failed assignment worth retrying differently, a contradiction a source could
    settle, or a branch the evidence opened. Each assignment so far is listed with
    its outcome; a follow-up must ask something none of them asked, and says which
    one is closest in differs_from. Proposed gaps come from the verifiers, each of
    whom saw only one researcher's work: adopt, merge or ignore them. Prefer fewer,
    broader follow-ups over many narrow ones. Return no follow-ups when the
    evidence answers the question well enough, or when rounds_left is 0.

    Finally, list in open_questions the material questions the evidence leaves
    open that no follow-up of yours will research, typed with their closure kind,
    so the report states its limits.
    """

    question: str = dspy.InputField()
    plan: list[dict[str, Any]] = dspy.InputField(desc="The planned directions, by id and name")
    assignments: list[dict[str, Any]] = dspy.InputField(
        desc="Every research assignment so far, with its round and outcome"
    )
    verified: list[dict[str, Any]] = dspy.InputField(
        desc="Every verified claim: claim_id, claim, source URL and supporting passage"
    )
    proposed_gaps: list[Gap] = dspy.InputField(
        desc="Open questions the verifiers named, and requirements the planner deferred"
    )
    researcher_tools: list[str] = dspy.InputField(
        desc="The tools a follow-up researcher has; required_tools come from these"
    )
    rounds_left: int = dspy.InputField(desc="Research rounds still allowed; 0 means none")
    max_follow_ups: int | None = dspy.InputField(
        desc="A limit the person set on directions per round; none means no limit"
    )
    format_problem: str = dspy.InputField(
        desc="Empty, or why your previous reply could not be read; return every field in its declared shape"
    )
    across: list[CrossFinding] = dspy.OutputField()
    follow_ups: list[FollowUp] = dspy.OutputField()
    open_questions: list[Direction] = dspy.OutputField()


#: Characters of a supporting passage the coordinator reads per claim.
PASSAGE_CHARS = 300


def verified_digest(audit: Any) -> list[dict[str, Any]]:
    """Each verified claim, compact: its ID, text, sources and a short passage."""

    rows = []
    for claim in audit.verified:
        edge = claim.evidence[0]
        quote = " ".join(edge.quote.split())
        rows.append(
            {
                "claim_id": claim.claim_id,
                "claim": claim.claim,
                "source_urls": sorted({row.source_url for row in claim.evidence}),
                "passage": quote if len(quote) <= PASSAGE_CHARS else quote[:PASSAGE_CHARS] + "…",
            }
        )
    return rows


def checked_across(
    findings: list[dict[str, Any]], verified_ids: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Findings that rest only on verified claims, and what was cut and why."""

    kept, cut = [], []
    for finding in findings:
        ids = list(finding.get("claim_ids") or [])
        unknown = [cid for cid in ids if cid not in verified_ids]
        known = [cid for cid in ids if cid in verified_ids]
        if unknown or not known:
            cut.append({"statement": finding["statement"], "unknown_claim_ids": unknown})
        if known:
            kept.append({**finding, "claim_ids": known})
    return kept, cut


def as_gap(direction: dict[str, Any]) -> dict[str, Any]:
    """A follow-up that will not be researched, kept as an open question."""

    fields = {key: value for key, value in direction.items() if key in Gap.model_fields}
    return Gap.model_validate({**fields, "gap_id": ""}).model_dump()


__all__ = [
    "Coordinate",
    "CrossFinding",
    "FollowUp",
    "as_gap",
    "checked_across",
    "verified_digest",
]
