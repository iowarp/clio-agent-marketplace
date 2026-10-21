"""Unit tests for ProvenanceStore.get_run_health's statistical gating
(#1218 r3 owner follow-up): the minimum-baseline-sample verdict gate and the
relative std floor. Uses hand-constructed metric values for deterministic
control over baseline tightness, rather than relying on the synthetic
pipeline's own randomness to (maybe) produce a freak-tight sample.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from phenotype_workload.provenance.store import MIN_BASELINE_SAMPLE, RELATIVE_STD_FLOOR, ProvenanceStore


def _seed_run(store: ProvenanceStore, run_id: str, mean_biomass: float) -> None:
    """Record a minimal completed run with a single mean_biomass metric --
    enough for get_run_health, without needing a full stage-execution chain.
    """
    store.begin_run(run_id, campaign="test", started_at="2026-01-01T00:00:00+00:00")
    store.record_metric(run_id, "mean_biomass", mean_biomass)
    store.end_run(run_id, "completed", ended_at="2026-01-01T00:00:01+00:00")


@pytest.fixture
def store(tmp_path: Path) -> ProvenanceStore:
    return ProvenanceStore(tmp_path / "provenance.sqlite")


class TestInsufficientBaselineGate:
    """The exact scenario that produced the false positive: a 5-run
    campaign's leave-one-out baseline (n=4) is tight enough that an
    ordinary run z-trips into what the OLD code called "anomalous". The
    fix must report "insufficient_baseline" instead, regardless of how
    large the (still-computed, still-visible) z is.
    """

    def test_tiny_std_small_sample_is_insufficient_not_anomalous(
        self, store: ProvenanceStore
    ) -> None:
        # 4 near-identical baseline runs (an accidentally tight small
        # sample) plus one run only modestly different -- under the OLD
        # code this divides by a near-zero std and explodes into a huge |z|.
        for i, value in enumerate([100.0, 100.001, 99.999, 100.0], start=1):
            _seed_run(store, f"run-{i:03d}", value)
        _seed_run(store, "run-005", 100.5)

        health = store.get_run_health("run-005")
        row = next(h for h in health if h["metric"] == "mean_biomass")
        assert row["baseline_n"] == 4
        assert row["baseline_n"] < MIN_BASELINE_SAMPLE
        assert row["verdict"] == "insufficient_baseline"
        # z is still computed and visible (for context/debugging) -- only
        # the verdict is gated, not the number itself.
        assert row["z"] != 0.0

    def test_same_shape_with_enough_baseline_and_a_real_deviation_is_anomalous(
        self, store: ProvenanceStore
    ) -> None:
        # 10 healthy baseline runs with ordinary ~1-2% noise, then one run
        # with a genuine, large (35%) deviation -- baseline_n=10 clears
        # MIN_BASELINE_SAMPLE, so the verdict is trusted.
        healthy = [100.0, 101.2, 99.1, 100.6, 98.9, 101.5, 99.7, 100.3, 99.4, 100.8]
        for i, value in enumerate(healthy, start=1):
            _seed_run(store, f"run-{i:03d}", value)
        _seed_run(store, "run-011", 135.0)

        health = store.get_run_health("run-011")
        row = next(h for h in health if h["metric"] == "mean_biomass")
        assert row["baseline_n"] == 10
        assert row["baseline_n"] >= MIN_BASELINE_SAMPLE
        assert row["verdict"] == "anomalous"
        assert abs(row["z"]) > 3


class TestRelativeStdFloor:
    """The std floor is a FRACTION of the baseline mean, not an absolute
    constant -- it must scale with each metric's own units, and must not
    suppress a genuine large deviation once baseline_n clears the gate.
    """

    def test_freakishly_tight_baseline_does_not_manufacture_a_false_positive(
        self, store: ProvenanceStore
    ) -> None:
        # 9 near-identical baseline runs (clears MIN_BASELINE_SAMPLE=8) with
        # an almost-zero natural std, plus one run only trivially (0.2%)
        # different -- without the relative floor this still divides by
        # ~0 and reads as a wild anomaly despite being a negligible
        # real-world difference.
        for i in range(1, 10):
            _seed_run(store, f"run-{i:03d}", 100.0 + (i % 2) * 0.0005)
        _seed_run(store, "run-010", 100.2)

        health = store.get_run_health("run-010")
        row = next(h for h in health if h["metric"] == "mean_biomass")
        assert row["baseline_n"] == 9
        floored_expected = RELATIVE_STD_FLOOR * abs(row["baseline_mean"])
        assert floored_expected > row["baseline_std"], "fixture must actually exercise the floor"
        assert abs(row["z"]) < 3
        assert row["verdict"] == "normal"

    def test_absolute_floor_guards_a_zero_baseline_mean(self, store: ProvenanceStore) -> None:
        # A baseline mean of exactly zero makes RELATIVE_STD_FLOOR * mean
        # zero too; MIN_BASELINE_STD is the last-resort guard against a
        # literal division by zero in that edge case.
        for i in range(1, 9):
            _seed_run(store, f"run-{i:03d}", 0.0)
        _seed_run(store, "run-009", 0.0)

        health = store.get_run_health("run-009")
        row = next(h for h in health if h["metric"] == "mean_biomass")
        assert row["baseline_n"] == 8
        assert row["z"] == 0.0
        assert row["verdict"] == "normal"

    def test_a_real_large_deviation_still_reads_as_anomalous_through_the_floor(
        self, store: ProvenanceStore
    ) -> None:
        # The floor must damp SAMPLING NOISE without masking a genuine
        # deviation: a tight baseline plus a 35%-off run (mirroring the
        # real calibration tamper) must still trip anomalous.
        for i in range(1, 9):
            _seed_run(store, f"run-{i:03d}", 100.0 + (i % 2) * 0.0005)
        _seed_run(store, "run-009", 135.0)

        health = store.get_run_health("run-009")
        row = next(h for h in health if h["metric"] == "mean_biomass")
        assert row["baseline_n"] == 8
        assert row["verdict"] == "anomalous"
        assert abs(row["z"]) > 3
