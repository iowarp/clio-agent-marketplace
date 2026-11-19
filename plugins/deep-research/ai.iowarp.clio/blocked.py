"""Whether a research round was blocked, from typed facts only.

A round is blocked when no researcher got a single successful search or fetch and the
reason is on the record: research-tool calls refused by a permission decision (a policy
or the person), or searches that failed with a typed "cannot search" code (every source
declined, none available, searching stopped). The researchers' prose is never read.
A blocked round is not "nothing found": the flow stops instead of sending the same
directions out again (2026-11-13: three rounds of refused searches on v0.9.7.1).
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .evidence import _web_payload

#: The researcher's research tools, as permission receipts name them.
RESEARCH_TOOLS = frozenset({"web_search", "web_fetch", "literature_search", "literature_lookup"})
#: The built-in servers those tools run on, as tool task records name them.
RESEARCH_SERVERS = frozenset({"web", "literature"})
#: Search error codes that mean searching cannot happen now, whatever the query.
BLOCKING_CODES = {
    "search_not_approved": "the person declined every search source; one can be allowed "
    "in Settings > Web search",
    "search_all_sources_unavailable": "every search source is unavailable right now",
    "search_stopped_by_person": "the person chose to stop searching",
    "search_disabled": "web search is turned off in Settings > Web search",
    "search_no_source": "no search source is turned on in Settings > Web search",
}


def _refused(receipt: dict[str, Any]) -> bool:
    return receipt.get("decision_status") == "auto_denied" or receipt.get("action") == "deny"


def round_block(
    tool_rows: list[dict[str, Any]],
    receipts_before: dict[str, Any],
    receipts_after: dict[str, Any],
) -> dict[str, Any] | None:
    """The typed reason this round's research could not run, or ``None``.

    Args:
        tool_rows: ``ctx.tool_results`` rows of this round's researchers.
        receipts_before: ``ctx.permission_receipts`` taken before the round.
        receipts_after: the same, taken after it.
    """

    codes: Counter[str] = Counter()
    for row in tool_rows:
        task = row.get("task") or {}
        backend = task.get("backend") or task.get("submitted_backend") or {}
        if task.get("kind") != "MCP" or backend.get("server") not in RESEARCH_SERVERS:
            continue
        body = _web_payload(row.get("value"))
        if body is not None and body.get("ok") is True:
            return None  # some research ran: the critic judges what it found
        code = str(((body or {}).get("error") or {}).get("code") or "")
        if code in BLOCKING_CODES:
            codes[code] += 1
    seen = {r.get("receipt_id") for r in receipts_before.get("receipts") or []}
    refused = [
        r
        for r in receipts_after.get("receipts") or []
        if r.get("receipt_id") not in seen
        and r.get("tool_name") in RESEARCH_TOOLS
        and _refused(r)
    ]
    if not codes and not refused:
        return None  # nothing on the record says research was blocked
    return {
        "refused_tools": sorted({str(r["tool_name"]) for r in refused}),
        "refusal_reasons": sorted({str(r.get("reason") or "") for r in refused} - {""}),
        "search_codes": dict(sorted(codes.items())),
    }


def blocked_message(block: dict[str, Any]) -> str:
    """The block in words, for the person and the agent that started the run."""

    parts = []
    if block.get("refused_tools"):
        why = ", ".join(block.get("refusal_reasons") or []) or "a permission decision"
        parts.append(
            f"every {', '.join(block['refused_tools'])} call was refused ({why}); "
            "allow these tools for this conversation or check the permission rules"
        )
    parts += [BLOCKING_CODES[code] for code in block.get("search_codes") or {}]
    return "Research could not run: " + "; ".join(parts) + "."


__all__ = ["BLOCKING_CODES", "RESEARCH_TOOLS", "blocked_message", "round_block"]
