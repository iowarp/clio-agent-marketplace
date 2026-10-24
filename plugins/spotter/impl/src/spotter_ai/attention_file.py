"""Verified local attention capture access; no SSH or network file fetching."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse

import numpy as np
from clio_schemas.attention import SparseAttentionRow
from safetensors import SafetensorError, safe_open

from spotter_ai.errors import ProvenanceError

HEALTH_KEYS = (
    "decode_steps_dropped",
    "decode_steps_unscored",
    "decode_steps_nonfinite",
    "restarts",
)


def verified_path(record: dict[str, Any], root: Path) -> Path:
    """Resolve within the configured capture root and verify size and digest."""
    stats = record["attention_stats"]
    uri = urlparse(str(stats.get("uri") or ""))
    if stats.get("error") or uri.scheme != "file" or uri.netloc not in {"", "localhost"}:
        raise ProvenanceError("attention_file_unavailable", "Capture has no usable local file")
    node_path = unquote(uri.path)
    # file:///C:/... is an absolute Windows path; POSIX captures may be mirrored locally.
    if re.match(r"^/[A-Za-z]:/", node_path):
        node_path = node_path[1:]
    root = root.resolve()
    suffix = PurePosixPath(node_path).parts[-2:]
    if any(part in {"..", "."} for part in suffix):
        raise ProvenanceError("attention_file_unavailable", "Invalid capture path")
    candidates = (Path(node_path), root.joinpath(*suffix))
    path = next(
        (p.resolve() for p in candidates if p.resolve().is_relative_to(root) and p.is_file()), None
    )
    if path is None:
        raise ProvenanceError(
            "attention_file_unavailable", "Capture is outside the configured local root or missing"
        )
    expected = str(stats.get("sha256") or "")
    size = stats.get("bytes")
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or not isinstance(size, int) or size <= 0:
        raise ProvenanceError(
            "attention_record_malformed", "Capture requires byte count and SHA-256"
        )
    if size > 512 * 1024 * 1024 or path.stat().st_size != size:
        raise ProvenanceError(
            "attention_file_mismatch", "Capture size does not match or exceeds 512 MiB"
        )
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != expected:
        raise ProvenanceError(
            "attention_file_mismatch", "Capture SHA-256 differs from the descriptor"
        )
    return path


def read_rows(
    record: dict[str, Any],
    root: Path,
    steps: list[int],
) -> tuple[int, list[SparseAttentionRow], list[tuple[int, int]], list[int]]:
    """Read selected decode rows only, refusing partial or inconsistent captures."""
    try:
        stats, used = record["attention_stats"], record["used"]
        if stats.get("format") != "safetensors":
            raise ValueError("capture format must be safetensors")
        if any(int(stats.get(key) or 0) for key in HEALTH_KEYS):
            raise ProvenanceError(
                "attention_capture_partial",
                "Skipped or restarted decode steps invalidate alignment",
            )
        total, count = int(used["num_prompt_tokens"]), int(used["num_decode_tokens"])
        if not 0 < total <= 1_000_000 or not count > 0:
            raise ValueError("invalid capture dimensions")
        selected = sorted(set(steps))
        if (
            not selected
            or len(selected) > 4096
            or any(step < 0 or step >= count for step in selected)
        ):
            raise ValueError("select 1 to 4096 in-range decode steps")
        path = verified_path(record, root)
        with safe_open(str(path), framework="np") as capture:
            if (capture.metadata() or {}).get("request_id") != used["request_id"]:
                raise ValueError("capture request identity differs from descriptor")
            ids = capture.get_tensor("prompt_token_ids")
            if ids.shape != (total,) or not np.issubdtype(ids.dtype, np.integer):
                raise ValueError("invalid captured prompt token IDs")
            raw_segments = capture.get_tensor("segments")
            if raw_segments.ndim != 2 or raw_segments.shape[1] < 2:
                raise ValueError("invalid segment dimensions")
            segments = [(int(lo), int(hi)) for lo, hi in raw_segments[:, :2]]
            cursor = 0
            for lo, hi in segments:
                if lo != cursor or hi <= lo or hi > total:
                    raise ValueError("segments must partition the captured prompt")
                cursor = hi
            if cursor != total:
                raise ValueError("segments do not cover the captured prompt")
            tensors = {
                name: capture.get_slice(name)
                for name in (
                    "topk_pos",
                    "val_all_avg",
                    "val_all_max",
                    "topk_residual",
                )
            }
            shapes = {name: tensor.get_shape() for name, tensor in tensors.items()}
            shape = shapes["topk_pos"]
            if len(shape) != 2 or shape[0] != count or shape[1] > total:
                raise ValueError("invalid sparse row dimensions")
            if shapes["val_all_avg"] != shape or shapes["val_all_max"] != shape:
                raise ValueError("sparse attention values and positions differ")
            if shapes["topk_residual"] not in ([count], [count, 1]):
                raise ValueError("invalid residual dimensions")
            rows = []
            for step in selected:
                pos = tensors["topk_pos"][step]
                if not np.issubdtype(pos.dtype, np.integer):
                    raise ValueError("sparse positions must be integers")
                rows.append(
                    SparseAttentionRow(
                        step=step,
                        positions=tuple(int(v) for v in pos),
                        mean=tuple(float(v) for v in tensors["val_all_avg"][step]),
                        peak=tuple(float(v) for v in tensors["val_all_max"][step]),
                        residual=float(np.asarray(tensors["topk_residual"][step]).item()),
                    )
                )
            return total, rows, segments, [int(v) for v in ids]
    except ProvenanceError:
        raise
    except (OSError, ValueError, TypeError, KeyError, IndexError, SafetensorError) as exc:
        raise ProvenanceError(
            "attention_record_malformed",
            "Capture could not be read consistently",
            {"reason": type(exc).__name__},
        ) from exc
