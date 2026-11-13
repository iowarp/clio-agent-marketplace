"""A researcher's findings as the critic reads them: typed claims, schema-validated.

A researcher returns its findings in ``workflow_state.packet.claims`` (text, FACT or
INFERENCE, fetched URL, exact quote) and keeps its Markdown for notes and the search
log. The critic then checks each claim against the passage it quotes instead of
re-reading a long Markdown answer (a round's critic input reached 114K characters
of free Markdown, 2026-11-13). A researcher that returns no typed claims still
passes its Markdown, as before; an entry that is not a valid claim is dropped and
counted, never silently.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError


class ResearchClaim(BaseModel):
    """One atomic finding with the fetched page and passage that support it."""

    text: str = Field(min_length=1)
    kind: Literal["FACT", "INFERENCE"] = "FACT"
    url: str = ""
    quote: str = ""


def typed_claims(result: Any) -> tuple[list[dict[str, Any]], int]:
    """The researcher's valid typed claims, and how many entries were not claims."""

    state = getattr(result, "workflow_state", None) or {}
    packet = state.get("packet") if isinstance(state, dict) else None
    rows = packet.get("claims") if isinstance(packet, dict) else None
    if not isinstance(rows, list):
        return [], 0
    claims: list[dict[str, Any]] = []
    invalid = 0
    for row in rows:
        try:
            claims.append(ResearchClaim.model_validate(row).model_dump())
        except ValidationError:
            invalid += 1
    return claims, invalid


__all__ = ["ResearchClaim", "typed_claims"]
