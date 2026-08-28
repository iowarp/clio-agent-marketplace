"""Per-batch report artifacts for the phenotype workload.

Each ``measure_cohort`` call is one batch -- a bounded slice of runs through
the phenotyping pipeline. Before this module existed, a batch's only trace
was a terminal-style summary line and rows in the provenance store; there was
nothing a human could open to see batch-level detail. This module renders
one batch (plus the campaign's running totals) to a JSON file under
``<data_dir>/reports/batch-NNN.json`` -- the path ``measure_cohort`` returns
as ``written_path``, one of clio-agent's recognized result-path keys
(``gact/artifacts/designation.py``'s ``RESULT_PATH_KEYS``), so the platform's
tool observer auto-registers it as a workspace artifact the moment the call
completes -- no agent action, no separate ``create_artifact`` call.
"""

from __future__ import annotations

import json
import statistics
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

#: Subdirectory, under a campaign's data directory, that batch reports are
#: written into.
REPORTS_DIRNAME = "reports"

#: The three per-run metrics every batch report tabulates, matching
#: :func:`phenotype_workload.pipeline.stages.predict`'s ``metrics`` output.
REPORT_METRICS = ("mean_biomass", "mean_leaf_area", "mean_height")


def next_batch_number(reports_dir: Path) -> int:
    """Determine the next 1-based batch sequence number.

    Scans ``reports_dir`` for existing ``batch-NNN.json`` files (written by
    any prior ``measure_cohort`` call against this same data directory) and
    returns one past the highest number found -- the same continuation
    convention :func:`phenotype_workload.workload._next_run_start_index` uses for
    run numbering.

    Args:
        reports_dir: The campaign's ``<data_dir>/reports`` directory.

    Returns:
        ``1`` if no prior batch reports exist, otherwise ``max(existing) + 1``.
    """
    if not reports_dir.exists():
        return 1
    numbers = []
    for child in reports_dir.iterdir():
        if not (child.is_file() and child.name.startswith("batch-") and child.suffix == ".json"):
            continue
        try:
            numbers.append(int(child.stem.split("-", 1)[1]))
        except (IndexError, ValueError):
            continue
    return max(numbers, default=0) + 1


def _stats(values: list[float]) -> dict[str, float]:
    """Compute mean/min/max for one metric's values, rounded for readability."""
    return {
        "mean": round(statistics.fmean(values), 6),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
    }


def write_batch_report(
    data_dir: Path,
    campaign: str,
    batch_runs: list[dict[str, Any]],
    campaign_runs: list[dict[str, Any]],
) -> Path:
    """Write one batch's report JSON and return its path.

    Agent story: ``measure_cohort`` calls this once per invocation, after its
    runs complete, so a human (or the platform's artifact panel, once the
    tool observer auto-registers the returned ``written_path``) has
    batch-level detail to open instead of only a terminal summary line.

    Args:
        data_dir: The campaign's data directory; the report is written to
            ``<data_dir>/reports/batch-NNN.json``.
        campaign: The campaign name recorded on the report (server-resolved
            config, not a per-call argument -- see :mod:`phenotype_workload.config`).
        batch_runs: This call's completed runs, in run order, each a dict
            with ``run_id``, ``mean_biomass``, ``mean_leaf_area``,
            ``mean_height``.
        campaign_runs: Every completed run recorded for this campaign so far
            (including this batch's own runs), same per-run shape as
            ``batch_runs``, used to compute the running campaign totals.

    Returns:
        The path the report was written to.

    Raises:
        ValueError: If ``batch_runs`` is empty -- there is nothing to report
            for a batch that completed zero runs (e.g. one halted by
            quarantine before its first run).
    """
    if not batch_runs:
        raise ValueError("cannot write a batch report for zero completed runs")

    reports_dir = data_dir / REPORTS_DIRNAME
    batch_number = next_batch_number(reports_dir)

    batch_stats = {metric: _stats([run[metric] for run in batch_runs]) for metric in REPORT_METRICS}
    campaign_totals: dict[str, Any] = {"run_count": len(campaign_runs)}
    for metric in REPORT_METRICS:
        campaign_totals[f"{metric}_avg"] = round(
            statistics.fmean(run[metric] for run in campaign_runs), 6
        )

    report = {
        "batch_number": batch_number,
        "campaign": campaign,
        "generated_at": datetime.now(UTC).isoformat(),
        "run_range": {"first": batch_runs[0]["run_id"], "last": batch_runs[-1]["run_id"]},
        "runs": batch_runs,
        "batch_stats": batch_stats,
        "campaign_totals": campaign_totals,
    }

    report_path = reports_dir / f"batch-{batch_number:03d}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report_path
