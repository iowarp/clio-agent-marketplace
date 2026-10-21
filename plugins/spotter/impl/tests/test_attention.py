"""Real SafeTensors reads with synthetic, explicitly known attention values."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from clio_schemas.attention import DECAYED_MAX, UNIFORM_MEAN
from fastmcp import Client
from safetensors.numpy import save_file

from spotter_ai.attention import AttentionEvidence
from spotter_ai.attention_file import read_rows
from spotter_ai.errors import ProvenanceError
from spotter_ai.server import create_server


class Query:
    """Test-only store holding one descriptor and recording filters."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.queries: list[dict[str, Any]] = []

    def query_attention_tasks(self, match: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        self.queries.append(match)
        return self.rows[:limit]


@pytest.fixture
def capture(tmp_path: Path) -> tuple[dict[str, Any], Path]:
    """Write a real file; expected weights and mass are calculable by hand."""
    root = tmp_path / "attention"
    path = root / "workflow" / "chatcmpl-test-abcd_g0.safetensors"
    path.parent.mkdir(parents=True)
    save_file(
        {
            "prompt_token_ids": np.array([10, 20, 30, 40], dtype=np.int64),
            "segments": np.array([[0, 2, 1], [2, 4, 1]], dtype=np.int64),
            "topk_pos": np.array([[0, 2], [0, 2]], dtype=np.int64),
            "val_all_avg": np.array([[0.2, 0.3], [0.4, 0.1]], dtype=np.float64),
            "val_all_max": np.array([[0.6, 0.7], [0.8, 0.5]], dtype=np.float64),
            "topk_residual": np.array([[0.5], [0.5]], dtype=np.float64),
        },
        str(path),
        metadata={"request_id": "chatcmpl-test-abcd"},
    )
    record = {
        "task_id": "chatcmpl-test-abcd:g0",
        "activity_id": "decode_attention",
        "used": {
            "request_id": "chatcmpl-test-abcd",
            "num_prompt_tokens": 4,
            "num_decode_tokens": 2,
        },
        "attention_stats": {
            "format": "safetensors",
            "uri": path.as_uri(),
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        },
    }
    return record, root


def test_mass_stays_uniform_while_heat_uses_shared_profile(
    capture: tuple[dict[str, Any], Path],
) -> None:
    """Duplicate selections count once and profile changes preserve total mass."""
    record, root = capture
    reader = AttentionEvidence(Query([record]), root)
    mean = reader.inspect("chatcmpl-test", [1, 0, 1], UNIFORM_MEAN)
    decay = reader.inspect("chatcmpl-test", [1, 0], DECAYED_MAX)
    assert mean["steps"] == [0, 1]
    assert mean["sources"][0]["score"] == pytest.approx(0.3)
    assert decay["sources"][0]["score"] == pytest.approx(2 / 3 * 0.6 + 1 / 3 * 0.8)
    assert [s["mass"] for s in mean["sources"]] == pytest.approx([0.3, 0.2])
    assert [s["mass"] for s in decay["sources"]] == pytest.approx([0.3, 0.2])
    assert decay["residual_mass"] == mean["residual_mass"] == 0.5
    assert mean["profile_revision"] != decay["profile_revision"]
    assert mean["sources"][0]["retained_tokens"] == 1
    assert len(mean["top_tokens"]) == 2
    assert mean["quarantine_changed"] is False


@pytest.mark.parametrize(
    "change,code",
    [
        ({"decode_steps_dropped": 1}, "attention_capture_partial"),
        ({"sha256": "0" * 64}, "attention_file_mismatch"),
        ({"sha256": ""}, "attention_record_malformed"),
        ({"uri": "ssh://node/private/file"}, "attention_file_unavailable"),
        ({"uri": "file://remotehost/private/file"}, "attention_file_unavailable"),
    ],
)
def test_refuses_incomplete_or_unverified_data(
    capture: tuple[dict[str, Any], Path],
    change: dict[str, Any],
    code: str,
) -> None:
    """Unreadable evidence never becomes a plausible attention score."""
    record, root = capture
    record["attention_stats"].update(change)
    with pytest.raises(ProvenanceError) as raised:
        read_rows(record, root, [0])
    assert raised.value.code == code


def test_requires_explicit_local_root(capture: tuple[dict[str, Any], Path], tmp_path: Path) -> None:
    """Even an existing descriptor path must be under the configured root."""
    record, _ = capture
    with pytest.raises(ProvenanceError, match="configured local root"):
        read_rows(record, tmp_path / "other", [0])


def test_mirror_uses_local_copy_and_rejects_bad_step(capture: tuple[dict[str, Any], Path]) -> None:
    """A remote descriptor can use an explicitly staged copy, with exact hash verification."""
    record, root = capture
    record["attention_stats"]["uri"] = (
        "file:///remote/node/workflow/chatcmpl-test-abcd_g0.safetensors"
    )
    assert read_rows(record, root, [0])[0] == 4
    with pytest.raises(ProvenanceError):
        read_rows(record, root, [2])


def test_ambiguous_capture_is_not_selected_arbitrarily(
    capture: tuple[dict[str, Any], Path],
) -> None:
    """Duplicated group-zero joins require resolution."""
    record, root = capture
    reader = AttentionEvidence(Query([record, copy.deepcopy(record)]), root)
    with pytest.raises(ProvenanceError, match="unambiguous"):
        reader.inspect("chatcmpl-test", [0], UNIFORM_MEAN)


def test_call_listing_has_no_payload_or_secrets(tmp_path: Path) -> None:
    """The listing carries identities only, even when full payloads are stored."""
    source = Query(
        [
            {
                "custom_metadata": {
                    "clio": {
                        "event_type": "lm.call",
                        "event_id": "call-1",
                        "turn_id": "turn-1",
                        "payload": {
                            "response_id": "response-1",
                            "model": "model",
                            "messages": ["secret"],
                        },
                    }
                }
            }
        ]
    )
    evidence = AttentionEvidence(source, tmp_path).list_calls("session-1")
    assert "secret" not in str(evidence)
    assert evidence["calls"][0]["response_id"] == "response-1"
    assert source.queries[0]["custom_metadata.clio.session_id"] == "session-1"


async def test_attention_mcp_is_read_only(
    capture: tuple[dict[str, Any], Path],
    tmp_path: Path,
) -> None:
    """The real MCP contract returns versioned evidence without invoking quarantine."""
    from spotter_ai.config import NativeQueryConfig
    from spotter_ai.providers.jsonl import JsonlProvider
    from spotter_ai.service import ProvenanceService

    record, root = capture
    journal = tmp_path / "events.jsonl"
    journal.write_text("", encoding="utf-8")
    provider = JsonlProvider(NativeQueryConfig(journal, tmp_path))
    server = create_server(
        service=ProvenanceService(provider, provider),
        attention=AttentionEvidence(Query([record]), root),
    )
    async with Client(server) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
        assert tools["inspect_attention"].annotations is not None
        assert tools["inspect_attention"].annotations.readOnlyHint is True
        result = await client.call_tool(
            "inspect_attention", {"response_id": "chatcmpl-test", "steps": [0, 1]}
        )
        assert result.structured_content is not None
        assert result.structured_content["profile_revision"] == UNIFORM_MEAN.revision
        assert result.structured_content["quarantine_changed"] is False
