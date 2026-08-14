"""Shared quarantine-sentinel mechanics for a campaign's data directory.

A single ``QUARANTINE`` file convention governs every place a campaign can be
halted or resumed:

- The campaign CLI (:mod:`spotter_ai.pipeline.campaign`) and the workload
  MCP server's ``measure_cohort`` both check for it before starting the next
  run and halt immediately if it is present.
- The forensic MCP server's ``raise_alert`` tool (:mod:`spotter_ai.server`)
  writes it once an agent has confirmed tampering.
- Both the forensic and workload MCP servers expose a ``lift_quarantine``
  tool that removes it, letting a human (or an agent acting on a human's
  explicit "continue") resume the campaign.

Centralizing the filename, path, and content format here guarantees all of
these agree on exactly the same sentinel file.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

#: Sentinel filename that, when present in a campaign's data directory,
#: halts the campaign before the next run starts.
QUARANTINE_FILENAME = "QUARANTINE"


def quarantine_path(data_dir: str | Path) -> Path:
    """Resolve the quarantine sentinel path for a campaign data directory.

    Args:
        data_dir: The campaign's data directory.

    Returns:
        Path to ``<data_dir>/QUARANTINE``.
    """
    return Path(data_dir) / QUARANTINE_FILENAME


def read_quarantine(data_dir: str | Path) -> str | None:
    """Read the quarantine sentinel's contents, if present.

    Args:
        data_dir: The campaign's data directory.

    Returns:
        The sentinel file's raw text content, or ``None`` if the campaign
        is not currently quarantined.
    """
    path = quarantine_path(data_dir)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def write_quarantine(data_dir: str | Path, run_id: str, reason: str) -> dict[str, Any]:
    """Write the quarantine sentinel, halting the campaign before its next run.

    Args:
        data_dir: The campaign's data directory.
        run_id: The run this quarantine concerns.
        reason: Human-readable justification for the quarantine.

    Returns:
        A confirmation dict with ``quarantined: True``, ``path``, ``run_id``,
        ``reason``, and ``timestamp``.
    """
    timestamp = datetime.now(UTC).isoformat()
    path = quarantine_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"run_id: {run_id}\nreason: {reason}\ntimestamp: {timestamp}\n",
        encoding="utf-8",
    )
    return {
        "quarantined": True,
        "path": str(path),
        "run_id": run_id,
        "reason": reason,
        "timestamp": timestamp,
    }


def lift_quarantine(data_dir: str | Path) -> dict[str, Any]:
    """Remove the quarantine sentinel if present, allowing the campaign to resume.

    Args:
        data_dir: The campaign's data directory.

    Returns:
        A confirmation dict with ``lifted`` (``True`` only if a sentinel was
        actually present and removed) and ``path``.
    """
    path = quarantine_path(data_dir)
    existed = path.exists()
    if existed:
        path.unlink()
    return {"lifted": existed, "path": str(path)}
