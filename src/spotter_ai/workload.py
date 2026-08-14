"""FastMCP tool server exposing the science-side campaign workload.

Server name: ``"phenotype-workload"``. This is the surface a science/ops
agent drives to actually run the phenotyping campaign -- as opposed to
:mod:`spotter_ai.server` (server name ``"spotter"``), which is the forensic
attribution surface a separate watcher agent uses to investigate it. The two
servers are deliberately split: this one knows nothing about forensics, and
critically, nothing it returns ever reveals whether a run was tampered with
(see ``run_campaign``'s fault-injection semantics below).

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

from spotter_ai.pipeline import campaign as campaign_module
from spotter_ai.pipeline import stages
from spotter_ai.provenance.store import ProvenanceStore
from spotter_ai.quarantine import lift_quarantine as quarantine_lift
from spotter_ai.quarantine import quarantine_path, read_quarantine

#: Filename, under a campaign's data directory, that plants a one-run
#: calibration-drift fault for run_campaign to apply silently. See
#: run_campaign's docstring for the exact indexing semantics.
FAULT_FILENAME = "fault.json"

#: The tamper magnitude applied when fault.json matches: calibration.json's
#: scale_factor is temporarily rewritten to this value.
TAMPERED_SCALE_FACTOR = 1.35

_RUN_DIR_PATTERN = re.compile(r"^run-(\d+)$")


def _next_run_start_index(runs_dir: Path) -> int:
    """Determine the global run number to continue numbering from.

    Scans ``runs_dir`` for existing ``run-NNN`` directories (written by any
    prior campaign CLI invocation or workload ``run_campaign`` call against
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
            independent of which ``run_campaign`` call produces it or that
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


def create_server(db_path: Path | str | None = None) -> FastMCP:
    """Build a phenotype-workload FastMCP tool server bound to a provenance store.

    Args:
        db_path: Path to the SQLite provenance database. Defaults to the
            store resolved from the ``SPOTTER_DB`` environment variable (see
            :func:`spotter_ai.provenance.store.default_db_path`).

    Returns:
        A configured :class:`fastmcp.FastMCP` server named
        ``"phenotype-workload"``, with all 3 science-side tools registered.
    """
    store = ProvenanceStore(db_path)
    mcp: FastMCP = FastMCP("phenotype-workload")

    @mcp.tool
    def run_campaign(
        runs: int = 14,
        campaign: str = "phenotype-2026",
        data_dir: str = "./campaign_data",
        sleep_s: float = 2.0,
    ) -> dict[str, Any]:
        """Run a batch of phenotyping runs in-process, recording full provenance.

        Agent story: a science/ops agent calls this to actually execute a
        campaign -- e.g. "run 14 more plants through the pipeline" -- and
        gets back exactly what a human watching a terminal would see: one
        line per run plus a final summary. It never needs to shell out to
        the CLI or know anything about the provenance store's internals.

        Run numbering continues from whatever already exists under
        ``<data_dir>/runs`` (so repeated calls against the same data_dir
        extend one campaign rather than colliding on run-001), and each
        run's seed equals its global run number, matching the campaign CLI's
        convention.

        Quarantine: exactly like the CLI, ``<data_dir>/QUARANTINE`` is
        checked before every run (including the first). If present, the
        campaign stops before starting that run and this returns a
        ``status: "halted"`` result naming SPOTTER AI and the sentinel's
        contents -- it never raises for this case.

        Fault injection (invisible to the caller): this tool takes NO
        tamper parameter. Instead, before each run, if
        ``<data_dir>/fault.json`` exists with the shape
        ``{"tamper_at": N}``, ``N`` is compared against the run's GLOBAL
        run-NNN number -- the same number embedded in its run_id (e.g.
        ``tamper_at: 12`` matches run-012) -- regardless of which
        run_campaign call actually produces that run. This matters because
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

        Args:
            runs: Number of runs to attempt in this invocation.
            campaign: Name of the campaign these runs belong to.
            data_dir: Directory holding ``calibration.json`` and
                ``runs/<run_id>/`` artifacts.
            sleep_s: Seconds to sleep between runs (default 2.0, paced for a
                live demo rather than a test).

        Returns:
            A dict with ``status`` (``"completed"`` or ``"halted"``),
            ``campaign``, ``runs`` (list of ``{"run_id", "mean_biomass"}``
            for each run completed in this invocation, in order),
            ``summary`` (``{"run_count", "mean_biomass_avg"}`` over this
            invocation's completed runs), and -- only when halted --
            ``message`` (the SPOTTER-AI quarantine notice).
        """
        data_dir_path = Path(data_dir)
        runs_dir = data_dir_path / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        calibration_path = data_dir_path / "calibration.json"

        campaign_module.ensure_calibration_file(calibration_path)
        original_calibration_text = calibration_path.read_text(encoding="utf-8")

        start_index = _next_run_start_index(runs_dir)
        completed: list[dict[str, Any]] = []

        for local_index in range(1, runs + 1):
            reason = read_quarantine(data_dir_path)
            if reason is not None:
                return {
                    "status": "halted",
                    "campaign": campaign,
                    "message": f"CAMPAIGN HALTED — quarantined by SPOTTER AI: {reason}",
                    "runs": completed,
                    "summary": _summarize_completed(completed),
                }

            global_index = start_index + local_index - 1
            run_id = f"run-{global_index:03d}"

            tampered_this_run = _fault_matches(data_dir_path, global_index)
            if tampered_this_run:
                campaign_module.tamper_calibration(calibration_path, TAMPERED_SCALE_FACTOR)

            try:
                metrics = campaign_module.run_single(
                    store=store,
                    run_id=run_id,
                    campaign=campaign,
                    seed=global_index,
                    run_dir=runs_dir / run_id,
                    calibration_path=calibration_path,
                )
            finally:
                if tampered_this_run:
                    calibration_path.write_text(original_calibration_text, encoding="utf-8")

            completed.append({"run_id": run_id, "mean_biomass": metrics["mean_biomass"]})

            if sleep_s:
                time.sleep(sleep_s)

        return {
            "status": "completed",
            "campaign": campaign,
            "runs": completed,
            "summary": _summarize_completed(completed),
        }

    @mcp.tool
    def campaign_status(data_dir: str = "./campaign_data") -> dict[str, Any]:
        """Report the runs recorded so far in a data directory and its quarantine state.

        Agent story: a science/ops agent calls this to check progress
        without re-running anything -- e.g. before deciding how many more
        runs to request, or to confirm a quarantine is (or isn't) in effect
        before trying run_campaign again.

        Args:
            data_dir: The campaign's data directory.

        Returns:
            A dict with ``data_dir``, ``runs`` (list of ``{"run_id",
            "status", "metrics"}`` for each run found under
            ``<data_dir>/runs`` that has a matching provenance record, in
            run-id order), ``run_count``, and ``quarantined`` (whether
            ``<data_dir>/QUARANTINE`` currently exists).
        """
        data_dir_path = Path(data_dir)
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
    def lift_quarantine(data_dir: str = "./campaign_data") -> dict[str, Any]:
        """Remove the QUARANTINE sentinel, letting run_campaign proceed again.

        Agent story: used for the "okay, continue" demo beat -- once a human
        has reviewed a forensic alert and decided the campaign should
        resume, a science/ops agent calls this (rather than needing the
        forensic server mounted) to clear the sentinel run_campaign checks
        before every run.

        Args:
            data_dir: The campaign's data directory (must match the one
                run_campaign / the CLI was invoked with).

        Returns:
            A dict with ``lifted`` (``True`` only if a sentinel was actually
            present and removed) and ``path``.
        """
        return quarantine_lift(data_dir)

    return mcp


def main() -> None:
    """Serve the phenotype-workload tool server over stdio using the default store."""
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
