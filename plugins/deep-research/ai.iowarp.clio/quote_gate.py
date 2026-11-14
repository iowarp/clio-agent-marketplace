"""The quote gate: a researcher's typed claim against the page it says it read.

Before any model reviews a researcher's claims, CLIO checks reality: did this
researcher successfully fetch the claim's URL, and is the quoted passage on that
page? A claim that passes carries its fetch handle and the page text around the
quote, so its verifier judges support from the passage instead of re-reading the
researcher's whole answer. A claim that fails is not judged here: it goes to the
verifier as unchecked, with the typed reason, and stays rejected with that reason
unless the verifier fetches the page and verifies it itself. Whether a passage
supports a claim is always a model's judgment; this module only reports whether
the passage exists where the researcher said it did.
"""

from __future__ import annotations

from typing import Any

from .audit import RejectedClaim
from .evidence import _quote_pattern, url_key

#: Characters of page text kept on each side of a quote for its verifier.
WINDOW = 600

#: Why a claim could not be checked against its page, keyed by typed reason.
GATE_REASONS = {
    "quote_missing": "the claim names no fetched page and quoted passage",
    "page_not_fetched": "the researcher did not successfully read the cited page",
    "quote_not_on_page": "the quoted passage is not on the page the researcher fetched",
}


def gate_claims(
    claims: list[dict[str, Any]], records: dict[str, dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    """Sort a researcher's typed claims by what its own fetches show.

    Args:
        claims: ``ResearchClaim`` rows from the researcher's packet.
        records: :func:`evidence.source_records` of that researcher's own fetches.

    Returns:
        ``bound`` claims (with ``fetch``, ``source_url``, ``source_title`` and
        ``page_text`` around the quote), ``unchecked`` claims (with a typed
        ``gate`` reason) and ``inferences`` (conclusions that cite no passage).
    """

    pages: dict[str, list[dict[str, Any]]] = {}
    for record in records.values():
        for key in {url_key(record["source_url"]), url_key(record["requested_url"])}:
            pages.setdefault(key, []).append(record)
    sorted_claims: dict[str, list[dict[str, Any]]] = {
        "bound": [],
        "unchecked": [],
        "inferences": [],
    }
    for claim in claims:
        url, quote = str(claim.get("url") or ""), str(claim.get("quote") or "")
        pattern = _quote_pattern(quote)
        if not url or pattern is None:
            if claim.get("kind") == "INFERENCE":
                sorted_claims["inferences"].append(dict(claim))
            else:
                sorted_claims["unchecked"].append(_unchecked(claim, "quote_missing"))
            continue
        fetched = pages.get(url_key(url), [])
        if not fetched:
            sorted_claims["unchecked"].append(_unchecked(claim, "page_not_fetched"))
            continue
        for record in fetched:
            content = record["content"]
            match = pattern.search(content)
            if match is None:
                continue
            start, end = max(0, match.start() - WINDOW), min(len(content), match.end() + WINDOW)
            sorted_claims["bound"].append(
                {
                    **claim,
                    "fetch": record["task_handle"],
                    "source_url": record["source_url"],
                    "source_title": " ".join(record["source_title"].split()),
                    "page_text": content[start:end],
                    "quote_repeats": pattern.search(content, match.start() + 1) is not None,
                }
            )
            break
        else:
            sorted_claims["unchecked"].append(_unchecked(claim, "quote_not_on_page"))
    return sorted_claims


def _unchecked(claim: dict[str, Any], code: str) -> dict[str, Any]:
    return {**claim, "gate": code, "reason": GATE_REASONS[code]}


def gate_rejections(
    unchecked: list[dict[str, Any]], verified_claims: set[str]
) -> list[RejectedClaim]:
    """Rejections for unchecked claims the verifier did not verify itself."""

    return [
        RejectedClaim(
            claim=row["text"],
            reason=f"Not verified: {row['reason']} (checked by CLIO).",
            source_url=str(row.get("url") or ""),
        )
        for row in unchecked
        if row["text"].strip() not in verified_claims
    ]


def gate_counts(gated: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """The gate's outcome for one packet, for the ``claims_gated`` run event."""

    reasons: dict[str, int] = {}
    for row in gated["unchecked"]:
        reasons[row["gate"]] = reasons.get(row["gate"], 0) + 1
    return {
        "bound": len(gated["bound"]),
        "unchecked": dict(sorted(reasons.items())),
        "inferences": len(gated["inferences"]),
    }


__all__ = ["GATE_REASONS", "WINDOW", "gate_claims", "gate_counts", "gate_rejections"]
