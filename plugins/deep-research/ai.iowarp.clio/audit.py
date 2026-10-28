"""Typed evidence-ledger continuity, requirements and audit validation."""

import hashlib
import json
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, Field, PrivateAttr, ValidationError, model_validator

from clio_agent.flows.outcomes import FlowStall

from .evidence import VerifiedClaim, bind_claims, claim_urls, merge_claims


class PermissionRequirement(BaseModel):
    """The exact authorization question, distinct from a receipt's granted scope."""

    scope: Literal["workspace", "session", "invocation"]
    scope_id: str = Field(
        min_length=1, description="Workspace ID, session ID, or exact permission ID"
    )


class Direction(BaseModel):
    """A model-selected question and the kind of work that could close it."""

    question: str = Field(min_length=1, description="One precise, self-contained question")
    why: str = Field(default="", description="Why its answer matters to the person's question")
    answer_looks_like: str = Field(
        default="",
        description="What would answer it: source families, data, period or jurisdiction",
    )
    closure_kind: Literal[
        "web_research", "workflow_action", "external_input", "unavailable_action", "design_limit"
    ]
    required_tools: list[str] = Field(default_factory=list)
    input_kind: Literal["", "permission"] = ""
    permission_requirement: PermissionRequirement | None = None
    action: str = Field(default="", description="Registered workflow action, otherwise empty")

    @model_validator(mode="after")
    def check_closure(self) -> "Direction":
        """Require an explicit tool requirement or action for executable work."""
        if self.closure_kind == "web_research" and not self.required_tools:
            raise ValueError("web_research requires the tools needed to answer it")
        if self.closure_kind == "workflow_action" and not self.action:
            raise ValueError("workflow_action requires a registered action name")
        if self.closure_kind != "workflow_action" and self.action:
            raise ValueError("only workflow_action may name an action")
        if self.input_kind and (self.closure_kind != "external_input" or not self.required_tools):
            raise ValueError("permission input requires external_input and its affected tools")
        if (self.input_kind == "permission") != (self.permission_requirement is not None):
            raise ValueError("permission input requires its exact permission_requirement scope")
        return self


class RejectedClaim(BaseModel):
    """A claim the critic would not stand behind, with its reason."""

    claim: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    source_url: str = ""


class Gap(Direction):
    """A material open question, retaining the work and tools needed to close it."""

    gap_id: str = Field(default="", description="Preserve a supplied ID; leave empty for a new gap")

    @model_validator(mode="after")
    def identify_gap(self) -> "Gap":
        """Keep closure identity stable across audit rounds and changed explanations."""
        key = [
            self.question,
            self.closure_kind,
            sorted(self.required_tools),
            self.action,
            self.input_kind,
            self.permission_requirement.model_dump() if self.permission_requirement else None,
        ]
        expected = "gap_" + hashlib.sha256(json.dumps(key).encode()).hexdigest()[:16]
        if self.gap_id and self.gap_id != expected:
            raise ValueError("gap_id does not identify this question and closure requirement")
        self.gap_id = expected
        return self


class GapResolution(BaseModel):
    """An explicit, inspectable reason an earlier gap no longer needs work."""

    gap_id: str
    basis: Literal["new_evidence", "scope_correction", "operator_evidence"]
    reason: str = Field(min_length=1)
    source_urls: list[str] = Field(default_factory=list)
    receipt_ids: list[str] = Field(default_factory=list)


class Audit(BaseModel):
    """The critic's complete audit: ``workflow_state.audit`` of its result."""

    verified: list[VerifiedClaim] = Field(default_factory=list)
    rejected: list[RejectedClaim] = Field(default_factory=list)
    gaps: list[Gap] = Field(default_factory=list)
    resolved_gaps: list[GapResolution] = Field(default_factory=list)
    _sources: dict[str, dict[str, Any]] = PrivateAttr(default_factory=dict)


def repair_context(
    section: Any,
    pending: list[Gap],
    earlier: Audit | None,
    records: dict[str, dict[str, Any]],
    operational_evidence: dict[str, Any] | None = None,
) -> tuple[Audit, dict[str, Any]]:
    """Retain bound ledger rows without accepting the invalid submitted audit.

    Gap IDs are derived from typed semantic fields for continuity only. The
    original submitted ID remains diagnostic evidence; the repaired audit still
    passes the ordinary strict validator. Unrepresentable requirements stall.
    """
    raw = section if isinstance(section, Mapping) else {}
    ledger = Audit()
    excluded: list[dict[str, Any]] = []
    for field, model in (("verified", VerifiedClaim), ("rejected", RejectedClaim)):
        rows = raw.get(field, [])
        if not isinstance(rows, list):
            excluded.append({"field": field, "problems": ["ledger field must be a list"]})
            continue
        for index, row in enumerate(rows):
            try:
                parsed = model.model_validate(row)
            except ValidationError as exc:
                excluded.append({"field": field, "row": index, "problems": str(exc)})
                continue
            if isinstance(parsed, VerifiedClaim):
                problems = bind_claims([parsed], records)
                if problems:
                    excluded.append({"field": field, "row": index, "problems": problems})
                    continue
                ledger.verified.append(parsed)
            else:
                ledger.rejected.append(parsed)
    _merge_ledger(ledger, earlier)
    gaps = {gap.gap_id: gap.model_copy(deep=True) for gap in pending}
    rows = raw.get("gaps", [])
    if not isinstance(rows, list):
        raise FlowStall(
            "critic_requirement_invalid",
            "audit gaps cannot be retained as typed requirements",
            step="verify",
            observed={"gaps": rows},
        )
    identity_repairs = []
    raw_open: dict[str, Gap] = {}
    for index, row in enumerate(rows):
        try:
            if not isinstance(row, Mapping):
                raise ValueError("gap must be an object")
            gap = Gap.model_validate({**row, "gap_id": ""})
        except (ValidationError, ValueError) as exc:
            raise FlowStall(
                "critic_requirement_invalid",
                "an invalid audit requirement needs corrected typed semantic fields",
                step="verify",
                observed={"row": index, "gap": row, "problem": str(exc)},
            ) from exc
        gaps[gap.gap_id] = gap
        raw_open[gap.gap_id] = gap
        if row.get("gap_id") and row["gap_id"] != gap.gap_id:
            identity_repairs.append({"row": index, "raw": dict(row), "canonical": gap.gap_id})
    resolutions = raw.get("resolved_gaps", [])
    if not isinstance(resolutions, list):
        excluded.append({"field": "resolved_gaps", "problems": ["ledger field must be a list"]})
        resolutions = []
    for index, row in enumerate(resolutions):
        try:
            resolution = GapResolution.model_validate(row)
        except ValidationError as exc:
            excluded.append({"field": "resolved_gaps", "row": index, "problems": str(exc)})
            continue
        candidate = Audit(verified=ledger.verified, resolved_gaps=[resolution])
        errors = _resolution_problems(
            candidate,
            {gap.gap_id: gap for gap in pending},
            raw_open,
            operational_evidence,
        )
        if errors:
            excluded.append({"field": "resolved_gaps", "row": index, "problems": errors})
        else:
            ledger.resolved_gaps.append(resolution)
    closed = {row.gap_id for row in ledger.resolved_gaps}
    ledger.gaps = [gap for key, gap in gaps.items() if key not in closed]
    ledger._sources = records
    return ledger, {
        "retained_claim_ids": [claim.claim_id for claim in ledger.verified],
        "retained_rejections": [claim.model_dump() for claim in ledger.rejected],
        "open_gap_ids": [gap.gap_id for gap in ledger.gaps],
        "gap_id_repairs": identity_repairs,
        "excluded_rows": excluded,
        "retained_resolutions": [row.model_dump() for row in ledger.resolved_gaps],
    }


def _merge_ledger(audit: Audit, earlier: Audit | None) -> None:
    """Carry earlier assertions unless the auditor explicitly reconsiders them."""
    if earlier is not None:
        verified = list(audit.verified)
        rejected = {(claim.claim, claim.source_url): claim for claim in audit.rejected}
        for claim in earlier.verified:
            withdrawn = any(
                row.claim == claim.claim
                and (not row.source_url or row.source_url in claim_urls(claim))
                for row in audit.rejected
            )
            if not withdrawn:
                verified.append(claim)
        for rejection in earlier.rejected:
            reconsidered = any(
                row.claim == rejection.claim
                and (not rejection.source_url or rejection.source_url in claim_urls(row))
                for row in audit.verified
            )
            if not reconsidered:
                rejected.setdefault((rejection.claim, rejection.source_url), rejection)
        audit.verified = merge_claims(verified)
        audit.rejected = list(rejected.values())
    audit.verified = merge_claims(audit.verified)


def _audit_of(
    result: Any,
    pending: list[Gap],
    earlier: Audit | None = None,
    operational_evidence: dict[str, Any] | None = None,
    *,
    carry_resolutions: bool = False,
) -> tuple[Audit | None, list[str]]:
    """The critic's typed audit, or why its ``workflow_state.audit`` is not one."""

    section = result.workflow_state.get("audit")
    if not isinstance(section, Mapping):
        return None, ["workflow_state.audit is missing or not an object"]
    try:
        audit = Audit.model_validate(section)
    except ValidationError as exc:
        return None, [
            f"audit.{'.'.join(str(p) for p in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
    known = {gap.gap_id: gap for gap in pending}
    remaining = {gap.gap_id: gap for gap in audit.gaps}
    _merge_ledger(audit, earlier)
    if carry_resolutions and earlier is not None:
        resolutions = {row.gap_id: row for row in audit.resolved_gaps}
        for row in earlier.resolved_gaps:
            if row.gap_id not in remaining:
                resolutions.setdefault(row.gap_id, row)
        audit.resolved_gaps = list(resolutions.values())
    problems = _resolution_problems(audit, known, remaining, operational_evidence)
    if problems:
        return None, problems
    closed = {row.gap_id for row in audit.resolved_gaps}
    for gap_id, gap in known.items():
        if gap_id not in closed:
            remaining.setdefault(gap_id, gap)
    audit.gaps = list(remaining.values())
    return audit, []


def _permission_covers(receipt: dict[str, Any], requirement: PermissionRequirement | None) -> bool:
    """Match recorded scope; never broaden one call or an opaque resource constraint."""
    if requirement is None or receipt.get("kind") not in {"tool", "external_mcp"}:
        return False
    if requirement.scope == "invocation":
        return receipt.get("permission_id") == requirement.scope_id
    identity_field = "workspace_id" if requirement.scope == "workspace" else "session_id"
    return bool(
        receipt.get("action") == f"allow_{requirement.scope}"
        and receipt.get("policy_scope") == requirement.scope
        and receipt.get("policy_scope_id") == requirement.scope_id
        and receipt.get(identity_field) == requirement.scope_id
        and receipt.get("resource_restricted") is False
    )


def _resolution_problems(
    audit: Audit,
    known: dict[str, Gap],
    remaining: dict[str, Gap],
    operational_evidence: dict[str, Any] | None,
) -> list[str]:
    """Validate exact closure scope and supporting evidence using the shared policy."""
    sources = {url for claim in audit.verified for url in claim_urls(claim)}
    receipts = {
        row["receipt_id"]: row
        for row in (operational_evidence or {}).get("receipts", [])
        if row.get("receipt_id")
    }
    problems = []
    for resolution in audit.resolved_gaps:
        gap = known.get(resolution.gap_id)
        if resolution.gap_id not in known or resolution.gap_id in remaining:
            problems.append(
                f"resolved_gaps: {resolution.gap_id} must identify an earlier gap, not an open one"
            )
        if resolution.basis == "new_evidence" and (
            not resolution.source_urls
            or not set(resolution.source_urls) <= sources
            or gap is not None
            and gap.input_kind == "permission"
        ):
            problems.append(
                f"resolved_gaps: {resolution.gap_id} needs supporting verified source URLs"
            )
        if resolution.basis == "operator_evidence":
            decisions = [receipts[key] for key in resolution.receipt_ids if key in receipts]
            valid = bool(
                gap is not None
                and gap.closure_kind == "external_input"
                and gap.input_kind == "permission"
                and resolution.receipt_ids
                and len(decisions) == len(resolution.receipt_ids)
                and all(
                    row.get("grantor") == "user"
                    and row.get("action") in {"allow", "allow_session", "allow_workspace"}
                    and row.get("decision_status") == "resolved"
                    for row in decisions
                )
                and all(_permission_covers(row, gap.permission_requirement) for row in decisions)
                and set(gap.required_tools) <= {row.get("tool_name") for row in decisions}
            )
            if not valid:
                problems.append(
                    f"resolved_gaps: {resolution.gap_id} needs attributable user receipts for its permission input"
                )
    return problems
