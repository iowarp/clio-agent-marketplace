"""Tests for the deterministic pipeline stages, the campaign CLI, and their
combined statistical/forensic properties: healthy run-to-run variance stays
tight, a calibration tamper produces a large, isolated anomaly, and the
quarantine sentinel halts the campaign immediately.
"""

from __future__ import annotations

import statistics
from pathlib import Path

import pytest

from spotter_ai.pipeline import stages
from spotter_ai.pipeline.campaign import build_arg_parser, run_campaign
from spotter_ai.provenance.store import ProvenanceStore


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point SPOTTER_DB at an isolated file under tmp_path for this test."""
    path = tmp_path / "spotter_provenance.sqlite"
    monkeypatch.setenv("SPOTTER_DB", str(path))
    return path


def _run(tmp_path: Path, **overrides: object) -> int:
    parser = build_arg_parser()
    args = parser.parse_args([])
    args.data_dir = str(tmp_path / "campaign_data")
    for key, value in overrides.items():
        setattr(args, key, value)
    return run_campaign(args)


class TestStagesPure:
    """Unit tests for the individual pure stage functions."""

    def test_ingest_is_deterministic(self, tmp_path: Path) -> None:
        raw_a = stages.read_json(stages.ingest("run-a", seed=42, run_dir=tmp_path / "a"))
        raw_b = stages.read_json(stages.ingest("run-b", seed=42, run_dir=tmp_path / "b"))
        assert raw_a["readings"] == raw_b["readings"]

    def test_ingest_different_seeds_differ(self, tmp_path: Path) -> None:
        raw_a = stages.read_json(stages.ingest("run-a", seed=1, run_dir=tmp_path / "a"))
        raw_b = stages.read_json(stages.ingest("run-b", seed=2, run_dir=tmp_path / "b"))
        assert raw_a["readings"] != raw_b["readings"]

    def test_ingest_produces_one_reading_per_plant(self, tmp_path: Path) -> None:
        raw = stages.read_json(stages.ingest("run-a", seed=1, run_dir=tmp_path))
        assert len(raw["readings"]) == stages.N_PLANTS
        plant_ids = {r["plant_id"] for r in raw["readings"]}
        assert len(plant_ids) == stages.N_PLANTS

    def test_calibrate_applies_scale_and_offset(self, tmp_path: Path) -> None:
        raw_path = stages.ingest("run-a", seed=1, run_dir=tmp_path)
        calibration_path = tmp_path / "calibration.json"
        stages.write_json(calibration_path, {"scale_factor": 2.0, "offset": 1.0})
        calibrated_path = stages.calibrate("run-a", tmp_path, raw_path, calibration_path)
        calibrated = stages.read_json(calibrated_path)
        raw = stages.read_json(raw_path)
        for raw_r, cal_r in zip(raw["readings"], calibrated["readings"], strict=True):
            assert cal_r["leaf_px"] == pytest.approx(raw_r["leaf_px"] * 2.0 + 1.0)
            assert cal_r["height_mm"] == pytest.approx(raw_r["height_mm"] * 2.0 + 1.0)
            # greenness is not calibrated
            assert cal_r["green_ratio"] == pytest.approx(raw_r["green_ratio"])

    def test_segment_rejects_duplicate_plant(self, tmp_path: Path) -> None:
        calibrated_path = tmp_path / "calibrated.json"
        readings = [
            {"plant_id": "plant-01", "leaf_px": 1.0, "height_mm": 1.0, "green_ratio": 0.5}
            for _ in range(2)
        ]
        stages.write_json(calibrated_path, {"run_id": "run-a", "readings": readings})
        with pytest.raises(ValueError, match="duplicate"):
            stages.segment("run-a", tmp_path, calibrated_path)

    def test_segment_rejects_missing_plant(self, tmp_path: Path) -> None:
        calibrated_path = tmp_path / "calibrated.json"
        stages.write_json(
            calibrated_path,
            {
                "run_id": "run-a",
                "readings": [
                    {"plant_id": "plant-01", "leaf_px": 1.0, "height_mm": 1.0, "green_ratio": 0.5}
                ],
            },
        )
        with pytest.raises(ValueError, match="missing"):
            stages.segment("run-a", tmp_path, calibrated_path)

    def test_full_stage_chain_produces_metrics(self, tmp_path: Path) -> None:
        calibration_path = tmp_path / "calibration.json"
        stages.write_json(calibration_path, dict(stages.DEFAULT_CALIBRATION))
        raw_path = stages.ingest("run-a", seed=1, run_dir=tmp_path)
        calibrated_path = stages.calibrate("run-a", tmp_path, raw_path, calibration_path)
        segments_path = stages.segment("run-a", tmp_path, calibrated_path)
        traits_path = stages.extract_traits("run-a", tmp_path, segments_path)
        predictions_path = stages.predict("run-a", tmp_path, traits_path)
        predictions = stages.read_json(predictions_path)
        assert set(predictions["metrics"]) == {"mean_biomass", "mean_leaf_area", "mean_height"}
        assert len(predictions["predictions"]) == stages.N_PLANTS
        for m in predictions["metrics"].values():
            assert m > 0


class TestCampaignCli:
    """Tests for the CLI runner: argument defaults, run naming, quarantine."""

    def test_defaults(self) -> None:
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.runs == 12
        assert args.campaign == "phenotype-2026"
        assert args.data_dir == "./campaign_data"
        assert args.tamper_at is None
        assert args.sleep == 0.0

    def test_run_id_format_and_provenance(self, tmp_path: Path, db_path: Path) -> None:
        exit_code = _run(tmp_path, runs=2)
        assert exit_code == 0
        store = ProvenanceStore(db_path)
        runs = store.list_runs()
        assert [r["run_id"] for r in runs] == ["run-001", "run-002"]
        for r in runs:
            assert r["status"] == "completed"
            assert r["stage_count"] == 5
            assert r["metrics"]["mean_biomass"] > 0

    def test_quarantine_halts_before_any_run(self, tmp_path: Path, db_path: Path) -> None:
        data_dir = tmp_path / "campaign_data"
        data_dir.mkdir(parents=True)
        (data_dir / "QUARANTINE").write_text(
            "run_id: run-003\nreason: tampering detected\n", encoding="utf-8"
        )
        exit_code = _run(tmp_path, runs=5)
        assert exit_code == 2
        store = ProvenanceStore(db_path)
        assert store.list_runs() == []

    def test_quarantine_halts_mid_campaign(self, tmp_path: Path, db_path: Path) -> None:
        data_dir = tmp_path / "campaign_data"
        parser = build_arg_parser()
        args = parser.parse_args([])
        args.data_dir = str(data_dir)
        args.runs = 100
        store = ProvenanceStore(db_path)

        # Run the campaign in a way that drops the sentinel after run-002.
        import spotter_ai.pipeline.campaign as campaign_mod

        original_run_single = campaign_mod.run_single
        call_count = {"n": 0}

        def run_single_then_quarantine(*a: object, **kw: object) -> dict[str, float]:
            call_count["n"] += 1
            result = original_run_single(*a, **kw)
            if call_count["n"] == 2:
                (data_dir / "QUARANTINE").write_text("reason: injected mid-run\n", encoding="utf-8")
            return result

        campaign_mod.run_single = run_single_then_quarantine
        try:
            exit_code = campaign_mod.run_campaign(args, store=store)
        finally:
            campaign_mod.run_single = original_run_single

        assert exit_code == 2
        runs = store.list_runs()
        assert len(runs) == 2
        assert all(r["status"] == "completed" for r in runs)


class TestForensicMargins:
    """The statistical acceptance criteria this whole substrate exists to prove:

    a healthy campaign's mean_biomass stays within |z| < 3 of its peers, and
    a calibration tamper shifts mean_biomass enough to score z > 5 -- with the
    diff between the tampered run and a healthy baseline showing exactly the
    calibrate-stage discrepancies and nothing else.
    """

    def test_healthy_campaign_all_within_z_3(self, tmp_path: Path, db_path: Path) -> None:
        exit_code = _run(tmp_path, runs=11)
        assert exit_code == 0
        store = ProvenanceStore(db_path)
        runs = store.list_runs()
        assert len(runs) == 11

        biomasses = [r["metrics"]["mean_biomass"] for r in runs]
        cv = statistics.stdev(biomasses) / statistics.fmean(biomasses)
        assert 0.01 < cv < 0.05, f"expected healthy CV in ~2-3% ballpark, got {cv:.4%}"

        for run in runs:
            health = store.get_run_health(run["run_id"])
            biomass_health = next(h for h in health if h["metric"] == "mean_biomass")
            z = biomass_health["z"]
            assert abs(z) < 3, f"{run['run_id']} biomass z={z:.2f}, expected < 3 healthy"
            assert biomass_health["verdict"] == "normal"

    def test_tampered_run_is_a_strong_anomaly(self, tmp_path: Path, db_path: Path) -> None:
        exit_code = _run(tmp_path, runs=12, tamper_at=12)
        assert exit_code == 0
        store = ProvenanceStore(db_path)
        runs = store.list_runs()
        assert len(runs) == 12

        health = store.get_run_health("run-012")
        biomass_health = next(h for h in health if h["metric"] == "mean_biomass")
        assert biomass_health["z"] > 5, f"expected tampered z > 5, got {biomass_health['z']:.2f}"
        assert biomass_health["verdict"] == "anomalous"

        # Calibration was restored after the tampered run, so run-011 (the
        # untampered run right before it) should look normal again.
        health_011 = store.get_run_health("run-011")
        biomass_011 = next(h for h in health_011 if h["metric"] == "mean_biomass")
        assert abs(biomass_011["z"]) < 3

    def test_diff_isolates_exactly_calibrate(self, tmp_path: Path, db_path: Path) -> None:
        exit_code = _run(tmp_path, runs=12, tamper_at=12)
        assert exit_code == 0
        store = ProvenanceStore(db_path)

        diff = store.diff_stage_executions("run-012", "run-001")
        discrepancies = diff["discrepancies"]

        assert discrepancies, "expected the tamper to surface as a discrepancy"
        assert all(d["stage"] == "calibrate" for d in discrepancies), discrepancies

        kinds = {d["kind"] for d in discrepancies}
        assert kinds == {"param_mismatch", "input_hash_mismatch"}

        param_discrepancy = next(d for d in discrepancies if d["kind"] == "param_mismatch")
        assert "scale_factor" in param_discrepancy["detail"]

        # No other stage should show a params/tool_version mismatch, and the
        # calibrate stage's own hash-equality flags should reflect the tamper.
        calibrate_stage = next(s for s in diff["stages"] if s["stage"] == "calibrate")
        assert calibrate_stage["params_equal"] is False
        assert calibrate_stage["input_hashes_equal"] is False
        assert calibrate_stage["tool_version_equal"] is True

        # params_equal and tool_version_equal are stable identity/config facts
        # and must hold everywhere but calibrate. input_hashes_equal is a raw
        # byte-equality fact, not a forensic judgment: segment/extract_traits/
        # predict each take the *previous stage's own per-run output* as
        # their sole input, so that hash legitimately differs between two
        # independently-seeded runs -- which is exactly why it is deliberately
        # NOT part of the curated discrepancies list checked above.
        for stage in diff["stages"]:
            if stage["stage"] == "calibrate":
                continue
            assert stage["params_equal"] is True, stage
            assert stage["tool_version_equal"] is True, stage

        ingest_stage = next(s for s in diff["stages"] if s["stage"] == "ingest")
        assert ingest_stage["input_hashes_equal"] is True  # ingest has no inputs

    def test_tamper_is_restored_after_the_tampered_run(self, tmp_path: Path, db_path: Path) -> None:
        exit_code = _run(tmp_path, runs=12, tamper_at=12)
        assert exit_code == 0
        calibration_path = tmp_path / "campaign_data" / "calibration.json"
        calibration = stages.read_json(calibration_path)
        assert calibration["scale_factor"] == pytest.approx(1.02)
