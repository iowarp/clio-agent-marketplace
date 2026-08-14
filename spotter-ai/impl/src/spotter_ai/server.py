"""FastMCP tool server exposing the SPOTTER-AI provenance store for forensic attribution.

Server name: ``"spotter"``. Every tool returns a bounded, JSON-serializable
dict and performs no network calls -- it only reads/writes the local
SQLite provenance store and the campaign data directory. This module makes
no use of DSPy; it is a plain read/write surface an external agent (of any
kind) can call over MCP to investigate a campaign.

Campaign name and data directory are workspace-fixed server config (see
:mod:`spotter_ai.config`), resolved once when :func:`create_server` builds
the server -- they are never model-supplied tool arguments (the defect this
fixed: ``campaign_health`` observed being called with ``campaign: null``,
because the model had no way to know what value belonged there).

Run directly with ``python -m spotter_ai.server`` to serve over stdio using
the store resolved from the ``SPOTTER_DB`` environment variable. For testing
or embedding, use :func:`create_server` to build an isolated server bound to
a specific database path.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from spotter_ai import config
from spotter_ai.provenance.store import ProvenanceStore
from spotter_ai.quarantine import lift_quarantine as quarantine_lift
from spotter_ai.quarantine import write_quarantine

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
        with all 9 forensic-attribution tools registered. The campaign name
        and data directory are resolved once here (from
        ``SPOTTER_CAMPAIGN``/``SPOTTER_DATA_DIR`` -- see
        :mod:`spotter_ai.config`) and closed over by every tool below; they
        are not re-read per call and are never tool arguments.
    """
    store = ProvenanceStore(db_path)
    campaign_name = config.resolve_campaign_name()
    data_dir_path = config.resolve_data_dir()
    mcp: FastMCP = FastMCP("spotter")

    @mcp.tool(title="List campaign runs")
    def list_runs() -> dict[str, Any]:
        """List every run in this campaign with its status, headline metrics, and store-wide totals.

        Agent story: an agent orienting itself in a campaign calls this
        first, to see how many runs exist, which finished, and their
        headline numbers -- so it can report explored-vs-total progress
        before drilling into any single run.

        Returns:
            A dict with ``"runs"`` (list of per-run summaries, scoped to
            this campaign: ``run_id``, ``campaign``, ``status``,
            ``started_at``, ``ended_at``, ``metrics``, ``stage_count``,
            ``artifact_count``) and ``"totals"`` (store-wide ``run_count``,
            ``stage_count``, ``artifact_count`` -- across every campaign the
            store has ever recorded, not just this one, since it reflects
            the whole database).
        """
        runs = store.list_runs(campaign=campaign_name)
        return {"runs": runs, "totals": store.totals()}

    @mcp.tool(title="Run health check")
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

    @mcp.tool(title="Campaign health sweep")
    def campaign_health() -> dict[str, Any]:
        """Sweep every completed run's health in this campaign in one call.

        This is the watcher's one-call sweep per wake.

        Agent story: run_health costs one LLM round PER run, which cannot
        keep up with a live campaign -- in a dry run the watcher was still
        checking run-010 when a 20-run campaign had already finished, so
        detection never happened. campaign_health computes the same
        leave-one-out z-scores for every completed run in a single call, so
        the watcher can triage an entire campaign each time it wakes and
        only spend a run_health/diff_runs round on the runs that actually
        come back anomalous.

        Returns:
            A dict with ``campaign`` (this server's resolved campaign name),
            ``runs_checked`` (number of completed runs evaluated),
            ``verdicts`` (one bounded row per run -- ``{"run_id", "verdict",
            "worst_metric", "worst_z", "value", "baseline_mean"}``,
            reporting only the single most anomalous metric per run, not the
            full metrics list -- use run_health for that), and ``anomalous``
            (the list of run_ids whose verdict is ``"anomalous"``). Uses the
            same floored-std z-score as run_health, since it is computed by
            the same code path.
        """
        verdicts = []
        for run in store.list_runs(campaign=campaign_name):
            if run["status"] != "completed":
                continue
            health = store.get_run_health(run["run_id"])
            if not health:
                continue
            worst = max(health, key=lambda h: abs(h["z"]))
            verdicts.append(
                {
                    "run_id": run["run_id"],
                    "verdict": worst["verdict"],
                    "worst_metric": worst["metric"],
                    "worst_z": worst["z"],
                    "value": worst["value"],
                    "baseline_mean": worst["baseline_mean"],
                }
            )
        anomalous = [v["run_id"] for v in verdicts if v["verdict"] == "anomalous"]
        return {
            "campaign": campaign_name,
            "runs_checked": len(verdicts),
            "verdicts": verdicts,
            "anomalous": anomalous,
        }

    @mcp.tool(title="Compare two runs")
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

    @mcp.tool(title="Trace run lineage")
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

    @mcp.tool(title="Read provenance artifact")
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

    @mcp.tool(title="Wait for new runs")
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

    @mcp.tool(title="Raise anomaly alert")
    def raise_alert(run_id: str, reason: str) -> dict[str, Any]:
        """Quarantine the campaign by writing a QUARANTINE sentinel file.

        Agent story: once an agent has forensically confirmed tampering (e.g.
        via run_health + diff_runs + read_artifact), it calls this to halt
        the campaign before another run starts -- the campaign CLI and the
        workload MCP server's measure_cohort both check for this sentinel
        before each run and stop immediately when it appears.

        Args:
            run_id: The run this alert concerns.
            reason: Human-readable justification for the quarantine.

        Returns:
            A dict with ``quarantined: True``, ``path`` (the sentinel file
            written), ``run_id``, ``reason``, and ``timestamp``.
        """
        return write_quarantine(data_dir_path, run_id, reason)

    @mcp.tool(title="Lift quarantine")
    def lift_quarantine() -> dict[str, Any]:
        """Remove the QUARANTINE sentinel, letting the campaign resume.

        Agent story: the SPOTTER watcher agent (which mounts only this
        forensic server, not the science-side workload server) uses this to
        resume the campaign once a human has reviewed an alert and
        explicitly said to continue -- e.g. after raise_alert turned out to
        be a false positive.

        Returns:
            A dict with ``lifted`` (``True`` only if a sentinel was actually
            present and removed) and ``path``.
        """
        return quarantine_lift(data_dir_path)

    return mcp


def main() -> None:
    """Serve the SPOTTER-AI tool server over stdio using the default store."""
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
