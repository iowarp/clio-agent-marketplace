"""FastMCP tool server exposing the science-side campaign workload.

Server name: ``"phenotype-workload"``. This is the surface a science/ops
agent drives to actually run the phenotyping campaign -- as opposed to
:mod:`spotter_ai.server` (server name ``"spotter"``), which is the forensic
attribution surface a separate watcher agent uses to investigate it. The two
servers are deliberately split: this one knows nothing about forensics, and
critically, nothing it returns ever reveals whether a run was tampered with
(see ``measure_cohort``'s fault-injection semantics below).

Campaign name and data directory are workspace-fixed server config (see
:mod:`spotter_ai.config`), resolved once when :func:`create_server` builds
the server -- they are never model-supplied tool arguments.

Run directly with ``python -m spotter_ai.workload`` to serve over stdio using
the store resolved from the ``SPOTTER_DB`` environment variable. For testing
or embedding, use :func:`create_server` to build an isolated server bound to
a specific database path.
"""

from __future__ import annotations

import re
import statistics
import time
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from spotter_ai import config, reports
from spotter_ai.pipeline import campaign as campaign_module
from spotter_ai.pipeline import stages
from spotter_ai.provenance.store import ProvenanceStore
from spotter_ai.quarantine import lift_quarantine as quarantine_lift
from spotter_ai.quarantine import quarantine_path, read_quarantine

#: Filename, under a campaign's data directory, that plants a one-run
#: calibration-drift fault for measure_cohort to apply silently. See
#: measure_cohort's docstring for the exact indexing semantics.
FAULT_FILENAME = "fault.json"

#: The tamper magnitude applied when fault.json matches: calibration.json's
#: scale_factor is temporarily rewritten to this value.
TAMPERED_SCALE_FACTOR = 1.35

#: Default pacing (seconds between runs) for a live demo -- see
#: measure_cohort's ``pace_seconds`` argument.
DEFAULT_PACE_SECONDS = 10.0

_RUN_DIR_PATTERN = re.compile(r"^run-(\d+)$")


def _next_run_start_index(runs_dir: Path) -> int:
    """Determine the global run number to continue numbering from.

    Scans ``runs_dir`` for existing ``run-NNN`` directories (written by any
    prior campaign CLI invocation or workload ``measure_cohort`` call against
    this same data directory) and returns one past the highest number found.

    Args:
        runs_dir: The campaign's ``<data_dir>/runs`` directory.

    Returns:
        ``1`` if no prior runs exist, otherwise ``max(existing) + 1``.
    """
    if not runs_dir.exists():
        return 1
    indices = [
        int(match.group(1))
        for child in runs_dir.iterdir()
        if child.is_dir() and (match := _RUN_DIR_PATTERN.match(child.name))
    ]
    return max(indices, default=0) + 1


def _existing_run_ids(runs_dir: Path) -> list[str]:
    """List existing ``run-NNN`` directory names under ``runs_dir``, sorted."""
    if not runs_dir.exists():
        return []
    names = [child.name for child in runs_dir.iterdir() if _RUN_DIR_PATTERN.match(child.name)]
    return sorted(names)


def _fault_matches(data_dir: Path, global_run_number: int) -> bool:
    """Check whether fault.json requests a tamper at this GLOBAL run number.

    Malformed or unreadable fault.json is treated as "no fault" rather than
    raised, since it is an out-of-band demo control file, not a pipeline
    artifact.

    Args:
        data_dir: The campaign's data directory.
        global_run_number: The run's global run-NNN number -- the same
            number embedded in its run_id (e.g. ``12`` for run-012) --
            independent of which ``measure_cohort`` call produces it or that
            call's own local iteration count.

    Returns:
        ``True`` if fault.json exists, parses, and its ``tamper_at`` equals
        ``global_run_number``.
    """
    fault_path = data_dir / FAULT_FILENAME
    if not fault_path.exists():
        return False
    try:
        fault = stages.read_json(fault_path)
    except (OSError, ValueError):
        return False
    return isinstance(fault, dict) and fault.get("tamper_at") == global_run_number


def _summarize_completed(completed: list[dict[str, Any]]) -> dict[str, Any]:
    if not completed:
        return {"run_count": 0, "mean_biomass_avg": None}
    values = [entry["mean_biomass"] for entry in completed]
    return {"run_count": len(completed), "mean_biomass_avg": round(statistics.fmean(values), 6)}


def _campaign_runs_for_report(store: ProvenanceStore, campaign: str) -> list[dict[str, Any]]:
    """Fetch every completed run in this campaign, shaped for a batch report.

    Args:
        store: The provenance store to query.
        campaign: The campaign name to filter by.

    Returns:
        A list of ``{"run_id", *reports.REPORT_METRICS}`` dicts, in
        ``store.list_runs`` order, for every completed run.
    """
    return [
        {"run_id": run["run_id"], **{k: run["metrics"][k] for k in reports.REPORT_METRICS}}
        for run in store.list_runs(campaign=campaign)
        if run["status"] == "completed"
    ]


def _finalize_batch_result(
    *,
    status: str,
    campaign: str,
    data_dir_path: Path,
    store: ProvenanceStore,
    completed: list[dict[str, Any]],
    completed_full: list[dict[str, Any]],
    message: str | None = None,
) -> dict[str, Any]:
    """Assemble measure_cohort's return payload, writing the batch report if any runs completed.

    Args:
        status: ``"completed"`` or ``"halted"``.
        campaign: The resolved campaign name.
        data_dir_path: The resolved campaign data directory.
        store: The provenance store, used to fetch the whole campaign's
            completed runs for the report's running totals.
        completed: This call's completed runs as ``{"run_id", "mean_biomass"}``
            -- the public, terminal-line-shaped result.
        completed_full: This call's completed runs as ``{"run_id",
            *reports.REPORT_METRICS}`` -- the fuller shape the batch report
            needs, built from the same loop without a second store round trip.
        message: The halt notice, when ``status == "halted"``.

    Returns:
        The tool's result dict, including ``report_path`` (``None`` when no
        runs completed in this call, so there is nothing to report).
    """
    result: dict[str, Any] = {
        "status": status,
        "campaign": campaign,
        "runs": completed,
        "summary": _summarize_completed(completed),
        "report_path": None,
    }
    if message is not None:
        result["message"] = message
    if completed_full:
        campaign_runs = _campaign_runs_for_report(store, campaign)
        report_path = reports.write_batch_report(
            data_dir_path, campaign, completed_full, campaign_runs
        )
        result["report_path"] = str(report_path)
    return result


def create_server(db_path: Path | str | None = None) -> FastMCP:
    """Build a phenotype-workload FastMCP tool server bound to a provenance store.

    Args:
        db_path: Path to the SQLite provenance database. Defaults to the
            store resolved from the ``SPOTTER_DB`` environment variable (see
            :func:`spotter_ai.provenance.store.default_db_path`).

    Returns:
        A configured :class:`fastmcp.FastMCP` server named
        ``"phenotype-workload"``, with all 3 science-side tools registered.
        The campaign name and data directory are resolved once here (from
        ``SPOTTER_CAMPAIGN``/``SPOTTER_DATA_DIR`` -- see
        :mod:`spotter_ai.config`) and closed over by every tool below; they
        are not re-read per call and are never tool arguments.
    """
    store = ProvenanceStore(db_path)
    campaign_name = config.resolve_campaign_name()
    data_dir_path = config.resolve_data_dir()
    mcp: FastMCP = FastMCP("phenotype-workload")

    @mcp.tool
    def measure_cohort(
        runs: int = 14, pace_seconds: float = DEFAULT_PACE_SECONDS
    ) -> dict[str, Any]:
        """Run a batch of measurement passes over the 60-plant cohort, recording full provenance.

        Named "measure_cohort" (not "run_campaign"): the campaign is fixed
        workspace config now, not a per-call concept, and what actually
        varies call to call is how many more measurement passes to take --
        each run pushes the same fixed cohort (:data:`~spotter_ai.pipeline.stages.N_PLANTS`
        plants) through ingest -> calibrate -> segment -> extract_traits ->
        predict and records one biomass/leaf-area/height reading per plant,
        summarized to run-level metrics.

        Agent story: a science/ops agent calls this to actually execute a
        batch -- e.g. "measure 14 more plants through the pipeline" -- and
        gets back exactly what a human watching a terminal would see: one
        line per run plus a final summary. It never needs to shell out to
        the CLI or know anything about the provenance store's internals.

        Run numbering continues from whatever already exists under this
        campaign's ``runs`` directory (so repeated calls extend one campaign
        rather than colliding on run-001), and each run's seed equals its
        global run number, matching the campaign CLI's convention.

        Quarantine: exactly like the CLI, the campaign's ``QUARANTINE``
        sentinel is checked before every run (including the first). If
        present, the campaign stops before starting that run and this
        returns a ``status: "halted"`` result naming SPOTTER AI and the
        sentinel's contents -- it never raises for this case.

        Fault injection (invisible to the caller): this tool takes NO
        tamper parameter. Instead, before each run, if the campaign data
        directory's ``fault.json`` exists with the shape
        ``{"tamper_at": N}``, ``N`` is compared against the run's GLOBAL
        run-NNN number -- the same number embedded in its run_id (e.g.
        ``tamper_at: 12`` matches run-012) -- regardless of which
        measure_cohort call actually produces that run. This matters because
        a real campaign is typically driven as a sequence of smaller
        batched calls (e.g. ``runs=8``, then ``runs=6``, ...); a demo
        operator can plan "tamper run 12" up front without knowing in
        advance which call's local iteration will land on it. For example:
        a first call with ``runs=8`` produces run-001..run-008, and a
        second call with ``runs=6`` and fault.json's ``tamper_at: 12``
        tampers the *fifth* run of that second call -- global id run-012 --
        not whatever run its local iteration count of 5 might suggest. When
        matched, ``calibration.json``'s ``scale_factor`` is rewritten to
        :data:`TAMPERED_SCALE_FACTOR` for that run only and restored
        immediately afterward. Nothing about this ever appears in this
        tool's return value or in any log this tool emits -- fault.json is
        the demo's ground-truth record for the forensic server to be
        judged against, and is left in place (never deleted) by this tool.

        Batch report: once at least one run completes in this call, a
        report JSON is written under the campaign data directory's
        ``reports/`` folder (see :mod:`spotter_ai.reports`) with this
        batch's per-run metrics table, batch-level mean/min/max stats, and
        the campaign's running totals. Its path comes back as
        ``report_path`` so the caller can register it as an artifact.

        Args:
            runs: Number of runs to attempt in this invocation.
            pace_seconds: Seconds to pace between runs -- NOT a literal
                "sleep for testing" delay, but the cadence a live demo runs
                at so a human watching can follow along (default: 10.0).

        Returns:
            A dict with ``status`` (``"completed"`` or ``"halted"``),
            ``campaign``, ``runs`` (list of ``{"run_id", "mean_biomass"}``
            for each run completed in this invocation, in order),
            ``summary`` (``{"run_count", "mean_biomass_avg"}`` over this
            invocation's completed runs), ``report_path`` (workspace-relative
            path to this batch's report JSON, or ``None`` if no run
            completed in this call), and -- only when halted -- ``message``
            (the SPOTTER-AI quarantine notice).
        """
        runs_dir = data_dir_path / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        calibration_path = data_dir_path / "calibration.json"

        campaign_module.ensure_calibration_file(calibration_path)
        original_calibration_text = calibration_path.read_text(encoding="utf-8")

        start_index = _next_run_start_index(runs_dir)
        completed: list[dict[str, Any]] = []
        completed_full: list[dict[str, Any]] = []

        for local_index in range(1, runs + 1):
            reason = read_quarantine(data_dir_path)
            if reason is not None:
                return _finalize_batch_result(
                    status="halted",
                    campaign=campaign_name,
                    data_dir_path=data_dir_path,
                    store=store,
                    completed=completed,
                    completed_full=completed_full,
                    message=f"CAMPAIGN HALTED — quarantined by SPOTTER AI: {reason}",
                )

            global_index = start_index + local_index - 1
            run_id = f"run-{global_index:03d}"

            tampered_this_run = _fault_matches(data_dir_path, global_index)
            if tampered_this_run:
                campaign_module.tamper_calibration(calibration_path, TAMPERED_SCALE_FACTOR)

            try:
                metrics = campaign_module.run_single(
                    store=store,
                    run_id=run_id,
                    campaign=campaign_name,
                    seed=global_index,
                    run_dir=runs_dir / run_id,
                    calibration_path=calibration_path,
                )
            finally:
                if tampered_this_run:
                    calibration_path.write_text(original_calibration_text, encoding="utf-8")

            completed.append({"run_id": run_id, "mean_biomass": metrics["mean_biomass"]})
            completed_full.append(
                {
                    "run_id": run_id,
                    "mean_biomass": metrics["mean_biomass"],
                    "mean_leaf_area": metrics["mean_leaf_area"],
                    "mean_height": metrics["mean_height"],
                }
            )

            if pace_seconds:
                time.sleep(pace_seconds)

        return _finalize_batch_result(
            status="completed",
            campaign=campaign_name,
            data_dir_path=data_dir_path,
            store=store,
            completed=completed,
            completed_full=completed_full,
        )

    @mcp.tool
    def campaign_status() -> dict[str, Any]:
        """Report the runs recorded so far for this campaign and its quarantine state.

        Agent story: a science/ops agent calls this to check progress
        without re-running anything -- e.g. before deciding how many more
        runs to request, or to confirm a quarantine is (or isn't) in effect
        before trying measure_cohort again.

        Returns:
            A dict with ``data_dir``, ``runs`` (list of ``{"run_id",
            "status", "metrics"}`` for each run found under this campaign's
            ``runs`` directory that has a matching provenance record, in
            run-id order), ``run_count``, and ``quarantined`` (whether the
            campaign's ``QUARANTINE`` sentinel currently exists).
        """
        runs_dir = data_dir_path / "runs"

        runs = []
        for run_id in _existing_run_ids(runs_dir):
            run = store.get_run(run_id)
            if run is None:
                continue
            runs.append(
                {
                    "run_id": run_id,
                    "status": run["status"],
                    "metrics": store.get_run_metrics(run_id),
                }
            )

        return {
            "data_dir": str(data_dir_path),
            "runs": runs,
            "run_count": len(runs),
            "quarantined": quarantine_path(data_dir_path).exists(),
        }

    @mcp.tool
    def lift_quarantine() -> dict[str, Any]:
        """Remove the QUARANTINE sentinel, letting measure_cohort proceed again.

        Agent story: used for the "okay, continue" demo beat -- once a human
        has reviewed a forensic alert and decided the campaign should
        resume, a science/ops agent calls this (rather than needing the
        forensic server mounted) to clear the sentinel measure_cohort checks
        before every run.

        Returns:
            A dict with ``lifted`` (``True`` only if a sentinel was actually
            present and removed) and ``path``.
        """
        return quarantine_lift(data_dir_path)

    return mcp


def main() -> None:
    """Serve the phenotype-workload tool server over stdio using the default store."""
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
