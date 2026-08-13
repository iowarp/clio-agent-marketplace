"""Campaign CLI runner: drives batches of pipeline runs through the provenance store.

Run as ``python -m spotter_ai.pipeline.campaign [options]``. Each invocation
runs a batch of :data:`~spotter_ai.pipeline.stages.N_PLANTS`-plant synthetic
runs through the five pipeline stages, recording every stage execution to the
:class:`~spotter_ai.provenance.store.ProvenanceStore` resolved from the
``SPOTTER_DB`` environment variable. Optionally injects a one-run calibration
drift fault (``--tamper-at``) and always honors a quarantine sentinel file
that halts the campaign the moment it appears.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from spotter_ai.pipeline import stages
from spotter_ai.provenance.store import ArtifactRef, ProvenanceStore

#: Sentinel filename that, when present in the data directory, halts the
#: campaign before starting another run.
QUARANTINE_FILENAME = "QUARANTINE"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the campaign CLI's argument parser.

    Returns:
        A configured :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog="spotter_ai.pipeline.campaign",
        description="Run a batch of synthetic plant-phenotyping pipeline runs "
        "with full provenance capture.",
    )
    parser.add_argument("--runs", type=int, default=12, help="number of runs (default: 12)")
    parser.add_argument(
        "--campaign",
        type=str,
        default="phenotype-2026",
        help="campaign name (default: phenotype-2026)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="./campaign_data",
        help="directory for calibration.json and per-run artifacts (default: ./campaign_data)",
    )
    parser.add_argument(
        "--tamper-at",
        type=int,
        default=None,
        help="1-based run number before which calibration.json's scale_factor is set to 1.35; "
        "restored after that run completes",
    )
    parser.add_argument(
        "--sleep", type=float, default=0.0, help="seconds to sleep between runs (default: 0)"
    )
    return parser


def _ensure_calibration_file(calibration_path: Path) -> None:
    if not calibration_path.exists():
        calibration_path.parent.mkdir(parents=True, exist_ok=True)
        stages.write_json(calibration_path, dict(stages.DEFAULT_CALIBRATION))


def _tamper_calibration(calibration_path: Path) -> None:
    calibration = stages.read_json(calibration_path)
    calibration["scale_factor"] = 1.35
    stages.write_json(calibration_path, calibration)


def run_single(
    store: ProvenanceStore,
    run_id: str,
    campaign: str,
    seed: int,
    run_dir: Path,
    calibration_path: Path,
) -> dict[str, float]:
    """Run one pipeline instance end to end, recording provenance throughout.

    Args:
        store: The provenance store to record this run's stage executions to.
        run_id: Unique identifier for this run, e.g. ``"run-001"``.
        campaign: Name of the campaign this run belongs to.
        seed: Deterministic seed for :func:`~spotter_ai.pipeline.stages.ingest`.
        run_dir: Directory this run's artifacts are written into.
        calibration_path: Path to the campaign's ``calibration.json``.

    Returns:
        The run-level metrics dict (``mean_biomass``, ``mean_leaf_area``,
        ``mean_height``) produced by the ``predict`` stage.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    store.begin_run(run_id, campaign, started_at=_now())
    try:
        t0 = _now()
        raw_path = stages.ingest(run_id, seed, run_dir)
        store.record_stage(
            run_id,
            "ingest",
            params={"seed": seed, "n_plants": stages.N_PLANTS},
            inputs=[],
            outputs=[ArtifactRef(raw_path, "json", "stage_output")],
            tool_version=stages.TOOL_VERSION,
            started_at=t0,
            ended_at=_now(),
        )

        t0 = _now()
        calibrated_path = stages.calibrate(run_id, run_dir, raw_path, calibration_path)
        calibration = stages.read_json(calibration_path)
        store.record_stage(
            run_id,
            "calibrate",
            params=dict(calibration),
            inputs=[
                ArtifactRef(raw_path, "json", "raw_readings"),
                ArtifactRef(calibration_path, "json", "calibration_config"),
            ],
            outputs=[ArtifactRef(calibrated_path, "json", "stage_output")],
            tool_version=stages.TOOL_VERSION,
            started_at=t0,
            ended_at=_now(),
        )

        t0 = _now()
        segments_path = stages.segment(run_id, run_dir, calibrated_path)
        store.record_stage(
            run_id,
            "segment",
            params={"n_plants": stages.N_PLANTS},
            inputs=[ArtifactRef(calibrated_path, "json", "stage_input")],
            outputs=[ArtifactRef(segments_path, "json", "stage_output")],
            tool_version=stages.TOOL_VERSION,
            started_at=t0,
            ended_at=_now(),
        )

        t0 = _now()
        traits_path = stages.extract_traits(run_id, run_dir, segments_path)
        store.record_stage(
            run_id,
            "extract_traits",
            params={"pixel_to_cm2": stages.PIXEL_TO_CM2},
            inputs=[ArtifactRef(segments_path, "json", "stage_input")],
            outputs=[ArtifactRef(traits_path, "json", "stage_output")],
            tool_version=stages.TOOL_VERSION,
            started_at=t0,
            ended_at=_now(),
        )

        t0 = _now()
        predictions_path = stages.predict(run_id, run_dir, traits_path)
        store.record_stage(
            run_id,
            "predict",
            params={
                "weight_leaf_area": stages.BIOMASS_WEIGHT_LEAF_AREA,
                "weight_height": stages.BIOMASS_WEIGHT_HEIGHT,
                "weight_greenness": stages.BIOMASS_WEIGHT_GREENNESS,
                "intercept": stages.BIOMASS_INTERCEPT,
            },
            inputs=[ArtifactRef(traits_path, "json", "stage_input")],
            outputs=[ArtifactRef(predictions_path, "json", "stage_output")],
            tool_version=stages.TOOL_VERSION,
            started_at=t0,
            ended_at=_now(),
        )

        predictions = stages.read_json(predictions_path)
        metrics: dict[str, float] = predictions["metrics"]
        for name, value in metrics.items():
            store.record_metric(run_id, name, value)

        store.end_run(run_id, "completed", ended_at=_now())
        return metrics
    except Exception:
        store.end_run(run_id, "failed", ended_at=_now())
        raise


def run_campaign(args: argparse.Namespace, store: ProvenanceStore | None = None) -> int:
    """Run a full campaign per the parsed CLI arguments.

    Args:
        args: Parsed arguments from :func:`build_arg_parser`.
        store: Provenance store to use. Defaults to a store resolved from the
            ``SPOTTER_DB`` environment variable.

    Returns:
        Process exit code: ``0`` on a completed campaign, ``2`` if the
        campaign was halted by a quarantine sentinel.
    """
    data_dir = Path(args.data_dir)
    runs_dir = data_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    calibration_path = data_dir / "calibration.json"
    quarantine_path = data_dir / QUARANTINE_FILENAME

    _ensure_calibration_file(calibration_path)
    original_calibration_text = calibration_path.read_text(encoding="utf-8")

    store = store if store is not None else ProvenanceStore()

    for i in range(1, args.runs + 1):
        if quarantine_path.exists():
            reason = quarantine_path.read_text(encoding="utf-8")
            print(f"CAMPAIGN HALTED — quarantined by SPOTTER AI: {reason}")
            return 2

        run_id = f"run-{i:03d}"
        tampered_this_run = args.tamper_at is not None and i == args.tamper_at
        if tampered_this_run:
            _tamper_calibration(calibration_path)

        try:
            metrics = run_single(
                store=store,
                run_id=run_id,
                campaign=args.campaign,
                seed=i,
                run_dir=runs_dir / run_id,
                calibration_path=calibration_path,
            )
        finally:
            if tampered_this_run:
                calibration_path.write_text(original_calibration_text, encoding="utf-8")

        headline = metrics.get("mean_biomass")
        print(f"{run_id}: mean_biomass={headline:.3f}")

        if args.sleep:
            time.sleep(args.sleep)

    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Command-line arguments (excluding the program name). Defaults
            to :data:`sys.argv[1:]`.

    Returns:
        Process exit code.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    return run_campaign(args)


if __name__ == "__main__":
    sys.exit(main())
