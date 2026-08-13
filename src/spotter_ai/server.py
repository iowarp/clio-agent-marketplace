"""FastMCP tool server exposing the SPOTTER-AI provenance store for forensic attribution.

Server name: ``"spotter"``. Every tool returns a bounded, JSON-serializable
dict and performs no network calls -- it only reads/writes the local
SQLite provenance store and the campaign data directory. This module makes
no use of DSPy; it is a plain read/write surface an external agent (of any
kind) can call over MCP to investigate a campaign.

Run directly with ``python -m spotter_ai.server`` to serve over stdio using
the store resolved from the ``SPOTTER_DB`` environment variable. For testing
or embedding, use :func:`create_server` to build an isolated server bound to
a specific database path.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from spotter_ai.provenance.store import ProvenanceStore

#: How often wait_for_new_runs polls the provenance store while waiting.
POLL_INTERVAL_S = 2.0

#: Cap on the number of characters returned by read_artifact's content field.
READ_ARTIFACT_CONTENT_CAP = 4000


def create_server(db_path: Path | str | None = None) -> FastMCP:
    """Build a SPOTTER-AI FastMCP tool server bound to a provenance store.

    Args:
        db_path: Path to the SQLite provenance database. Defaults to the
            store resolved from the ``SPOTTER_DB`` environment variable (see
            :func:`spotter_ai.provenance.store.default_db_path`).

    Returns:
        A configured :class:`fastmcp.FastMCP` server named ``"spotter"``,
        with all 7 forensic-attribution tools registered.
    """
    store = ProvenanceStore(db_path)
    mcp: FastMCP = FastMCP("spotter")

    @mcp.tool
    def list_runs(campaign: str | None = None) -> dict[str, Any]:
        """List every run with its status, headline metrics, and store-wide totals.

        Agent story: an agent orienting itself in a campaign calls this
        first, to see how many runs exist, which finished, and their
        headline numbers -- so it can report explored-vs-total progress
        before drilling into any single run.

        Args:
            campaign: If given, only runs in this campaign are listed.

        Returns:
            A dict with ``"runs"`` (list of per-run summaries: ``run_id``,
            ``campaign``, ``status``, ``started_at``, ``ended_at``,
            ``metrics``, ``stage_count``, ``artifact_count``) and
            ``"totals"`` (store-wide ``run_count``, ``stage_count``,
            ``artifact_count``).
        """
        runs = store.list_runs(campaign=campaign)
        return {"runs": runs, "totals": store.totals()}

    @mcp.tool
    def run_health(run_id: str) -> dict[str, Any]:
        """Score a run's metrics against every other completed run via z-score.

        Agent story: after spotting a suspicious headline number, an agent
        calls this to get a quantitative anomaly score per metric instead of
        eyeballing a single value -- the verdict field is what it can act on
        directly (e.g. escalate to diff_runs when anomalous).

        Args:
            run_id: The run to evaluate.

        Returns:
            A dict with ``"run_id"`` and ``"metrics"``: a list of
            ``{"metric", "value", "baseline_mean", "baseline_std", "z",
            "verdict"}`` dicts, one per metric the run recorded. ``verdict``
            is ``"normal"`` when ``abs(z) < 3``, else ``"anomalous"``.

        Raises:
            ValueError: If ``run_id`` does not exist.
        """
        if store.get_run(run_id) is None:
            raise ValueError(f"run_id {run_id!r} not found")
        return {"run_id": run_id, "metrics": store.get_run_health(run_id)}

    @mcp.tool
    def diff_runs(run_id: str, baseline_run_id: str) -> dict[str, Any]:
        """Compare two runs stage-by-stage and isolate forensically significant differences.

        Agent story: once a run looks anomalous, an agent calls this against
        a known-healthy baseline run to pinpoint exactly which stage
        diverged and how -- separating expected per-run variation (each run
        is independently seeded) from a genuine configuration or code change.

        Args:
            run_id: The run under investigation.
            baseline_run_id: A known-healthy run to compare it against.

        Returns:
            A dict with ``run_id``, ``baseline_run_id``, ``stages`` (per-stage
            comparison: ``params_equal``, ``input_hashes_equal``,
            ``tool_version_equal``, ``output_summary_deltas``), and
            ``discrepancies`` (a list of ``{"stage", "kind", "detail"}``
            entries capturing only the forensically significant mismatches).

        Raises:
            ValueError: If either run_id does not exist.
        """
        if store.get_run(run_id) is None:
            raise ValueError(f"run_id {run_id!r} not found")
        if store.get_run(baseline_run_id) is None:
            raise ValueError(f"baseline_run_id {baseline_run_id!r} not found")
        return store.diff_stage_executions(run_id, baseline_run_id)

    @mcp.tool
    def trace_lineage(run_id: str, stage: str | None = None) -> dict[str, Any]:
        """Trace a run's stage chain backward from its last stage (or a given one).

        Agent story: an agent that has found a bad artifact calls this to
        walk backward through exactly the stages that produced it -- inputs,
        outputs, artifact ids, hashes, and roles at each hop -- to find where
        in the chain the anomaly was introduced.

        Args:
            run_id: The run to trace.
            stage: If given, trace only the ancestry of this stage (itself
                and everything that ran before it), not the stages after it.

        Returns:
            A dict with ``run_id``, ``stage_filter``, and ``chain``: a list
            of stage-execution dicts ordered from most recent to earliest,
            each with ``stage``, ``tool_version``, ``started_at``,
            ``ended_at``, ``params``, ``inputs``, ``outputs`` (the latter two
            being lists of ``{artifact_id, sha256, path, kind, role,
            summary}``).

        Raises:
            ValueError: If the run has no recorded stages, or ``stage`` does
                not appear among them.
        """
        chain = store.trace_lineage(run_id, stage=stage)
        return {"run_id": run_id, "stage_filter": stage, "chain": chain}

    @mcp.tool
    def read_artifact(artifact_id: int) -> dict[str, Any]:
        """Read one artifact's path, content hash, and (capped) content.

        Agent story: after trace_lineage or diff_runs points at a specific
        artifact id, an agent calls this to actually read what that artifact
        contained, to confirm or refute a hypothesis about the anomaly.

        Args:
            artifact_id: The artifact's id, as returned by other tools.

        Returns:
            A dict with ``path``, ``sha256``, and ``content`` (the artifact's
            text content, truncated to
            :data:`READ_ARTIFACT_CONTENT_CAP` characters).

        Raises:
            ValueError: If no artifact with this id is recorded, or its file
                no longer exists on disk.
        """
        artifact = store.get_artifact(artifact_id)
        if artifact is None:
            raise ValueError(f"artifact_id {artifact_id} not found")
        path = Path(artifact["path"])
        if not path.exists():
            raise ValueError(f"artifact_id {artifact_id} path no longer exists: {path}")
        content = path.read_text(encoding="utf-8", errors="replace")
        return {
            "path": artifact["path"],
            "sha256": artifact["sha256"],
            "content": content[:READ_ARTIFACT_CONTENT_CAP],
        }

    @mcp.tool
    async def wait_for_new_runs(known_run_ids: list[str], timeout_s: float = 300) -> dict[str, Any]:
        """Long-poll for a completed run not already known to the caller.

        Agent story: an agent that has finished investigating the runs it
        knows about calls this to block efficiently until the campaign
        produces a new completed run worth looking at, instead of busy-polling
        list_runs itself.

        Args:
            known_run_ids: Run ids the caller has already seen; any
                completed run not in this set counts as new.
            timeout_s: Maximum time to wait, in seconds.

        Returns:
            ``{"new_runs": [...]}`` (the newly completed runs' summaries, in
            the same shape as list_runs) as soon as at least one appears, or
            ``{"timed_out": True}`` if none appears before ``timeout_s``
            elapses.
        """
        known = set(known_run_ids)
        deadline = time.monotonic() + timeout_s
        while True:
            runs = store.list_runs()
            new_runs = [r for r in runs if r["run_id"] not in known and r["status"] == "completed"]
            if new_runs:
                return {"new_runs": new_runs}
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {"timed_out": True}
            await asyncio.sleep(min(POLL_INTERVAL_S, remaining))

    @mcp.tool
    def raise_alert(run_id: str, reason: str, data_dir: str = "./campaign_data") -> dict[str, Any]:
        """Quarantine the campaign by writing a QUARANTINE sentinel file.

        Agent story: once an agent has forensically confirmed tampering (e.g.
        via run_health + diff_runs + read_artifact), it calls this to halt
        the campaign before another run starts -- the campaign CLI checks for
        this sentinel before each run and exits immediately when it appears.

        Args:
            run_id: The run this alert concerns.
            reason: Human-readable justification for the quarantine.
            data_dir: The campaign's data directory (must match the one the
                running campaign CLI was invoked with).

        Returns:
            A dict with ``quarantined: True``, ``path`` (the sentinel file
            written), ``run_id``, ``reason``, and ``timestamp``.
        """
        timestamp = datetime.now(UTC).isoformat()
        path = Path(data_dir) / "QUARANTINE"
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

    return mcp


def main() -> None:
    """Serve the SPOTTER-AI tool server over stdio using the default store."""
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
