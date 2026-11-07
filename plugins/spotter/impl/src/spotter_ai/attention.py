"""Read-only attention evidence for SPOTTER using CLIO's shared reduction rules."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Protocol

from clio_schemas.attention import AttentionProfile, display_intensities, reduce_attention

from spotter_ai.attention_file import read_rows
from spotter_ai.errors import ProvenanceError


class AttentionQuery(Protocol):
    """The bounded internal Flowcept query used for capture evidence."""

    def query_attention_tasks(self, match: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        """Return matching descriptor or invocation records."""
        ...


class AttentionEvidence:
    """Inspect captures without calling CLIO or changing any store."""

    def __init__(self, source: AttentionQuery, files_dir: Path) -> None:
        self.source = source
        self.files_dir = files_dir

    def list_calls(self, session_id: str, limit: int = 100) -> dict[str, Any]:
        """List bounded model-call identities that can join to attention descriptors."""
        if not session_id or not 1 <= limit <= 200:
            raise ProvenanceError("invalid_argument", "Provide a session and limit from 1 to 200")
        rows = self.source.query_attention_tasks(
            {
                "subtype": "ai_model_invocation",
                "custom_metadata.clio.session_id": session_id,
            },
            limit + 1,
        )
        calls = []
        for row in rows[:limit]:
            clio = (row.get("custom_metadata") or {}).get("clio") or {}
            payload = clio.get("payload") or {}
            response_id = payload.get("response_id") or clio.get("response_id")
            if clio.get("event_type") != "lm.call" or not response_id:
                continue
            calls.append(
                {
                    "event_id": clio.get("event_id"),
                    "session_id": session_id,
                    "turn_id": clio.get("turn_id"),
                    "response_id": response_id,
                    "model": payload.get("model") or clio.get("model"),
                }
            )
        for call in calls:
            call.update(self._capture_summary(call["response_id"]))
        return {
            "calls": calls,
            "truncated": len(rows) > limit,
            "scope": "configured Flowcept store",
            "capture_verified": False,
        }

    def _group_zero(self, response_id: str) -> list[dict[str, Any]]:
        """The group-zero capture descriptors joined to one provider response ID."""
        records = self.source.query_attention_tasks(
            {
                "activity_id": "decode_attention",
                "used.request_id": {"$regex": f"^{re.escape(response_id)}-"},
            },
            33,
        )
        if len(records) > 32:
            raise ProvenanceError("attention_record_unavailable", "Capture join exceeds its bound")
        return [row for row in records if str(row.get("task_id", "")).endswith(":g0")]

    def _capture_summary(self, response_id: str) -> dict[str, Any]:
        """Whether a capture descriptor exists and how many decode steps it records."""
        try:
            records = self._group_zero(response_id)
        except ProvenanceError:
            return {"capture_available": False, "decode_steps": None}
        if len(records) != 1:
            return {"capture_available": False, "decode_steps": None}
        used = records[0].get("used") or {}
        steps = used.get("num_decode_tokens")
        return {
            "capture_available": True,
            "decode_steps": int(steps) if isinstance(steps, int | float) else None,
        }

    def inspect(
        self,
        response_id: str,
        steps: list[int] | None,
        profile: AttentionProfile,
    ) -> dict[str, Any]:
        """Reduce captured decode steps (all of them when ``steps`` is empty), preserving
        mass and missingness.

        Coordinates are captured token positions, not inferred image patches or
        transcript character offsets. Attention strength alone proves no attack.
        """
        if not response_id or len(response_id) > 256:
            raise ProvenanceError(
                "invalid_argument",
                "Provide an exact provider response ID from spotter_list_attention_calls",
            )
        records = self._group_zero(response_id)
        if len(records) != 1:
            raise ProvenanceError(
                "attention_record_unavailable",
                "Expected one unambiguous group-zero capture"
                if records
                else "No attention capture is recorded for this response ID",
            )
        record = records[0]
        total, rows, segments, token_ids = read_rows(record, self.files_dir, steps)
        try:
            reduced = reduce_attention(rows, total, profile)
        except ValueError as exc:
            raise ProvenanceError("attention_record_malformed", str(exc)) from exc
        raw_scores = [reduced.block_score(range(lo, hi)) for lo, hi in segments]
        intensities = display_intensities(raw_scores, profile)
        sections = [
            {
                "token_start": lo,
                "token_end": hi,
                "score": raw_scores[index],
                "intensity": intensities[index],
                "mass": sum(reduced.mean_mass[lo:hi]),
                "retained_tokens": sum(v > 0 for v in reduced.retained_steps[lo:hi]),
            }
            for index, (lo, hi) in enumerate(segments)
        ]
        top = sorted(
            (i for i in range(total) if reduced.retained_steps[i]),
            key=lambda i: (-reduced.scores[i], i),
        )[:100]
        return {
            "response_id": response_id,
            "request_id": record["used"]["request_id"],
            "capture_sha256": record["attention_stats"]["sha256"],
            "profile": profile.model_dump(mode="json"),
            "profile_revision": profile.revision,
            "steps": list(reduced.steps),
            "selection": "explicit steps" if steps else "every captured decode step",
            "weights": list(reduced.weights),
            "residual_mass": reduced.residual,
            "sources": sections,
            "top_tokens": [
                {
                    "position": i,
                    "token_id": token_ids[i],
                    "score": reduced.scores[i],
                    "mass": reduced.mean_mass[i],
                    "retained_steps": reduced.retained_steps[i],
                }
                for i in top
            ],
            "mass_semantics": "uniform mean over unique selected captured decode steps",
            "coordinate_space": "captured prompt tokens",
            "limitations": [
                "Sparse capture: absent positions are unretained, not zero attention.",
                "Token positions do not establish image or transcript coordinates.",
                "Attention strength alone is not evidence of poisoning.",
            ],
        }
