"""The quote gate: claims checked against the researcher's own fetches before a critic reads them."""

from __future__ import annotations

import sys
from typing import Any

from test_deep_research_flow import (
    Children,
    Planner,
    ScriptedCtx,
    audit,
    claim,
    flow_module,
    make_flow,
    of,
    run,
    source_fixture,
)

gate = sys.modules[flow_module.gate_claims.__module__]
evidence = sys.modules[flow_module.source_records.__module__]

PAGE = "Intro text. " * 80 + "passage 1" + " Later text." * 80


def records(content: str = PAGE, owner: str = "task_1") -> dict[str, Any]:
    row = source_fixture(1, owner)
    row["value"]["content"] = content
    return evidence.source_records([row], {owner})


def finding(**fields: Any) -> dict[str, Any]:
    return {
        "text": "claim 1",
        "kind": "FACT",
        "url": "https://example.org/1",
        "quote": "passage 1",
    } | fields


def test_a_quote_on_the_fetched_page_binds_with_the_text_around_it() -> None:
    (bound,) = gate.gate_claims([finding()], records())["bound"]
    assert bound["fetch"] == "fetch_1" and bound["source_url"] == "https://example.org/1"
    assert "passage 1" in bound["page_text"] and bound["quote_repeats"] is False
    assert len(bound["page_text"]) <= len("passage 1") + 2 * gate.WINDOW
    # Anchors and wrapped whitespace do not change which page or passage it is.
    moved = finding(url="https://EXAMPLE.org/1#section", quote="passage\n 1")
    assert gate.gate_claims([moved], records())["bound"][0]["fetch"] == "fetch_1"


def test_unbound_claims_carry_their_typed_reason() -> None:
    gated = gate.gate_claims(
        [
            finding(quote="not on the page"),
            finding(url="https://example.org/never-read"),
            finding(quote=""),
            finding(kind="INFERENCE", url="", quote=""),
        ],
        records(),
    )
    assert [row["gate"] for row in gated["unchecked"]] == [
        "quote_not_on_page",
        "page_not_fetched",
        "quote_missing",
    ]
    assert gated["bound"] == [] and len(gated["inferences"]) == 1
    assert gate.gate_counts(gated) == {
        "bound": 0,
        "unchecked": {"page_not_fetched": 1, "quote_missing": 1, "quote_not_on_page": 1},
        "inferences": 1,
    }


def test_a_repeated_quote_is_flagged_for_its_critic() -> None:
    (bound,) = gate.gate_claims([finding()], records("passage 1 and again passage 1"))["bound"]
    assert bound["quote_repeats"] is True


class ResearcherFetched(ScriptedCtx):
    """The researcher (task_1) fetched source 1; critics fetch nothing themselves."""

    async def tool_results(self, handle: str) -> list[dict[str, Any]]:
        return [source_fixture(1, handle)] if handle == "task_1" else []


class TypedResearcher(Children):
    def __init__(self, audits: list[dict[str, Any]], claims: list[dict[str, Any]]) -> None:
        super().__init__(audits)
        self.claims = claims

    def __call__(self, target: str, payload: Any) -> dict[str, Any]:
        if target == "researcher":
            return {"answer": "notes", "workflow_state": {"packet": {"claims": self.claims}}}
        return super().__call__(target, payload)


def test_a_critic_can_verify_from_the_researchers_fetch() -> None:
    ctx = ResearcherFetched(TypedResearcher([audit([claim(1)])], [finding()]))
    result = run(make_flow(Planner(["a"]), max_rounds=0), ctx)
    (packet,) = of(ctx, "critic")[0]["input"]["packets"]
    assert packet["claims"][0]["fetch"] == "fetch_1"
    assert result["verified"] == [claim(1)]
    assert {
        "event": "claims_gated",
        "round": 1,
        "direction": "d1",
        "bound": 1,
        "unchecked": {},
        "inferences": 0,
    } in ctx.events


def test_an_unchecked_claim_stays_rejected_unless_its_critic_verifies_it() -> None:
    wrong = finding(text="claim 9", quote="a passage the page lacks")
    ctx = ResearcherFetched(TypedResearcher([audit()], [wrong]))
    result = run(make_flow(Planner(["a"]), max_rounds=0), ctx)
    assert result["rejected"] == [
        {
            "claim": "claim 9",
            "reason": "Not verified: the quoted passage is not on the page the researcher "
            "fetched (checked by CLIO).",
            "source_url": "https://example.org/1",
        }
    ]

    # The critic fetched and verified the exact claim itself: it is not rejected.
    ctx = ResearcherFetched(TypedResearcher([audit([claim(1)])], [finding(quote="absent")]))
    result = run(make_flow(Planner(["a"]), max_rounds=0), ctx)
    assert result["verified"] == [claim(1)] and result["rejected"] == []


def test_a_repeated_quote_gets_a_unique_passage_from_the_page() -> None:
    page = "Ratio 10x at error 1e-3. Intro. Ratio 10x at error 1e-4 for SZ3."
    (bound,) = gate.gate_claims([finding(quote="Ratio 10x at error")], records(page))["bound"]
    assert bound["quote_repeats"] is True
    unique = bound["unique_quote"]
    assert unique.startswith("Ratio 10x at error") and page.count(unique) == 1
    assert evidence._quote_pattern(unique).search(page).start() == 0
    # A quote that occurs once needs nothing more.
    (single,) = gate.gate_claims([finding(quote="for SZ3")], records(page))["bound"]
    assert "unique_quote" not in single
    # Text that repeats for longer than the bound cannot be told apart: none is invented.
    periodic = "passage 1 again. " * 60
    (same,) = gate.gate_claims([finding(quote="passage 1")], records(periodic))["bound"]
    assert same["quote_repeats"] is True and "unique_quote" not in same
