"""Contract tests for the FastMCP "spotter" tool server, exercised in-memory
against a small campaign recorded into a tmp_path SQLite provenance store.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from spotter_ai.pipeline.campaign import build_arg_parser, run_campaign
from spotter_ai.provenance.store import ProvenanceStore
from spotter_ai.server import create_server


@pytest.fixture
def small_campaign(tmp_path: Path) -> tuple[Path, Path]:
    """Run a tiny 3-run healthy campaign into an isolated tmp_path store.

    Returns:
        A ``(db_path, data_dir)`` tuple.
    """
    db_path = tmp_path / "provenance.sqlite"
    data_dir = tmp_path / "campaign_data"
    store = ProvenanceStore(db_path)

    parser = build_arg_parser()
    args = parser.parse_args([])
    args.data_dir = str(data_dir)
    args.runs = 3

    exit_code = run_campaign(args, store=store)
    assert exit_code == 0
    return db_path, data_dir


class TestListRuns:
    async def test_contract_shape(self, small_campaign: tuple[Path, Path]) -> None:
        db_path, _ = small_campaign
        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool("list_runs", {})

        data = result.data
        assert set(data) == {"runs", "totals"}
        assert len(data["runs"]) == 3
        for run in data["runs"]:
            assert set(run) >= {
                "run_id",
                "campaign",
                "status",
                "started_at",
                "ended_at",
                "metrics",
                "stage_count",
                "artifact_count",
            }
            assert run["status"] == "completed"
            assert run["stage_count"] == 5
            assert run["metrics"]["mean_biomass"] > 0

        totals = data["totals"]
        assert totals["run_count"] == 3
        assert totals["stage_count"] == 15
        assert totals["artifact_count"] > 0

    async def test_campaign_filter(self, small_campaign: tuple[Path, Path]) -> None:
        db_path, _ = small_campaign
        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool("list_runs", {"campaign": "does-not-exist"})
        assert result.data["runs"] == []


class TestRunHealth:
    async def test_contract_shape(self, small_campaign: tuple[Path, Path]) -> None:
        db_path, _ = small_campaign
        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool("run_health", {"run_id": "run-001"})

        data = result.data
        assert data["run_id"] == "run-001"
        metric_names = {m["metric"] for m in data["metrics"]}
        assert metric_names == {"mean_biomass", "mean_leaf_area", "mean_height"}
        for m in data["metrics"]:
            assert set(m) == {"metric", "value", "baseline_mean", "baseline_std", "z", "verdict"}
            assert m["verdict"] in {"normal", "anomalous"}

    async def test_unknown_run_raises(self, small_campaign: tuple[Path, Path]) -> None:
        db_path, _ = small_campaign
        server = create_server(db_path)
        async with Client(server) as client:
            with pytest.raises(ToolError):
                await client.call_tool("run_health", {"run_id": "run-999"})


class TestCampaignHealth:
    """The batched sweep the watcher calls once per wake instead of one
    run_health round per run -- must reach the same verdicts run_health
    would, for every completed run, in a single tool call.
    """

    async def test_contract_shape(self, small_campaign: tuple[Path, Path]) -> None:
        db_path, _ = small_campaign
        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool("campaign_health", {})

        data = result.data
        assert set(data) == {"campaign", "runs_checked", "verdicts", "anomalous"}
        assert data["campaign"] is None
        assert data["runs_checked"] == 3
        assert len(data["verdicts"]) == 3
        for row in data["verdicts"]:
            assert set(row) == {
                "run_id",
                "verdict",
                "worst_metric",
                "worst_z",
                "value",
                "baseline_mean",
            }
            assert row["verdict"] in {"normal", "anomalous"}
            assert row["worst_metric"] in {"mean_biomass", "mean_leaf_area", "mean_height"}
        assert isinstance(data["anomalous"], list)

    async def test_healthy_campaign_all_normal(self, tmp_path: Path) -> None:
        db_path = tmp_path / "provenance.sqlite"
        data_dir = tmp_path / "campaign_data"
        store = ProvenanceStore(db_path)
        parser = build_arg_parser()
        args = parser.parse_args([])
        args.data_dir = str(data_dir)
        args.runs = 11
        assert run_campaign(args, store=store) == 0

        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool("campaign_health", {})

        data = result.data
        assert data["runs_checked"] == 11
        assert data["anomalous"] == []
        assert all(row["verdict"] == "normal" for row in data["verdicts"])

    async def test_tampered_campaign_flags_exactly_run_012(self, tmp_path: Path) -> None:
        db_path = tmp_path / "provenance.sqlite"
        data_dir = tmp_path / "campaign_data"
        store = ProvenanceStore(db_path)
        parser = build_arg_parser()
        args = parser.parse_args([])
        args.data_dir = str(data_dir)
        args.runs = 12
        args.tamper_at = 12
        assert run_campaign(args, store=store) == 0

        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool("campaign_health", {})

        data = result.data
        assert data["runs_checked"] == 12
        assert data["anomalous"] == ["run-012"]

        tampered_row = next(row for row in data["verdicts"] if row["run_id"] == "run-012")
        assert tampered_row["verdict"] == "anomalous"
        assert tampered_row["worst_metric"] == "mean_biomass"
        assert tampered_row["worst_z"] > 5, f"expected worst_z > 5, got {tampered_row['worst_z']}"

        for row in data["verdicts"]:
            if row["run_id"] == "run-012":
                continue
            assert row["verdict"] == "normal", row

    async def test_campaign_filter(self, small_campaign: tuple[Path, Path]) -> None:
        db_path, _ = small_campaign
        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool("campaign_health", {"campaign": "does-not-exist"})
        assert result.data == {
            "campaign": "does-not-exist",
            "runs_checked": 0,
            "verdicts": [],
            "anomalous": [],
        }


class TestDiffRuns:
    async def test_contract_shape(self, small_campaign: tuple[Path, Path]) -> None:
        db_path, _ = small_campaign
        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool(
                "diff_runs", {"run_id": "run-002", "baseline_run_id": "run-001"}
            )

        data = result.data
        assert data["run_id"] == "run-002"
        assert data["baseline_run_id"] == "run-001"
        assert len(data["stages"]) == 5
        for stage in data["stages"]:
            assert set(stage) == {
                "stage",
                "params_equal",
                "input_hashes_equal",
                "tool_version_equal",
                "output_summary_deltas",
            }
        # Two healthy runs: no forensic discrepancies expected.
        assert data["discrepancies"] == []

    async def test_unknown_run_raises(self, small_campaign: tuple[Path, Path]) -> None:
        db_path, _ = small_campaign
        server = create_server(db_path)
        payload = {"run_id": "run-999", "baseline_run_id": "run-001"}
        async with Client(server) as client:
            with pytest.raises(ToolError):
                await client.call_tool("diff_runs", payload)


class TestTraceLineage:
    async def test_full_chain_is_backward_ordered(self, small_campaign: tuple[Path, Path]) -> None:
        db_path, _ = small_campaign
        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool("trace_lineage", {"run_id": "run-001"})

        data = result.data
        assert data["run_id"] == "run-001"
        chain = data["chain"]
        assert [entry["stage"] for entry in chain] == [
            "predict",
            "extract_traits",
            "segment",
            "calibrate",
            "ingest",
        ]
        expected_ref_keys = {"artifact_id", "sha256", "path", "kind", "role", "summary"}
        for entry in chain:
            assert "inputs" in entry and "outputs" in entry
            for artifact_ref in entry["inputs"] + entry["outputs"]:
                assert set(artifact_ref) == expected_ref_keys

    async def test_stage_filter_truncates_ancestry(self, small_campaign: tuple[Path, Path]) -> None:
        db_path, _ = small_campaign
        server = create_server(db_path)
        payload = {"run_id": "run-001", "stage": "segment"}
        async with Client(server) as client:
            result = await client.call_tool("trace_lineage", payload)

        chain = result.data["chain"]
        assert [entry["stage"] for entry in chain] == ["segment", "calibrate", "ingest"]

    async def test_unknown_stage_raises(self, small_campaign: tuple[Path, Path]) -> None:
        db_path, _ = small_campaign
        server = create_server(db_path)
        payload = {"run_id": "run-001", "stage": "not-a-stage"}
        async with Client(server) as client:
            with pytest.raises(ToolError):
                await client.call_tool("trace_lineage", payload)


class TestReadArtifact:
    async def test_reads_capped_content(self, small_campaign: tuple[Path, Path]) -> None:
        db_path, _ = small_campaign
        server = create_server(db_path)
        async with Client(server) as client:
            lineage = await client.call_tool("trace_lineage", {"run_id": "run-001"})
            artifact_id = lineage.data["chain"][0]["outputs"][0]["artifact_id"]

            result = await client.call_tool("read_artifact", {"artifact_id": artifact_id})

        data = result.data
        assert set(data) == {"path", "sha256", "content"}
        assert data["path"].endswith("predictions.json")
        assert len(data["sha256"]) == 64
        assert len(data["content"]) <= 4000
        assert '"predictions"' in data["content"]

    async def test_unknown_artifact_raises(self, small_campaign: tuple[Path, Path]) -> None:
        db_path, _ = small_campaign
        server = create_server(db_path)
        async with Client(server) as client:
            with pytest.raises(ToolError):
                await client.call_tool("read_artifact", {"artifact_id": 999999})


class TestWaitForNewRuns:
    async def test_returns_immediately_when_unknown_completed_run_exists(
        self, small_campaign: tuple[Path, Path]
    ) -> None:
        db_path, _ = small_campaign
        server = create_server(db_path)
        async with Client(server) as client:
            started = time.monotonic()
            result = await client.call_tool(
                "wait_for_new_runs", {"known_run_ids": ["run-001", "run-002"], "timeout_s": 300}
            )
            elapsed = time.monotonic() - started

        assert elapsed < 1.0
        data = result.data
        assert "new_runs" in data
        assert [r["run_id"] for r in data["new_runs"]] == ["run-003"]

    async def test_times_out_fast_when_nothing_new(self, small_campaign: tuple[Path, Path]) -> None:
        db_path, _ = small_campaign
        server = create_server(db_path)
        async with Client(server) as client:
            started = time.monotonic()
            result = await client.call_tool(
                "wait_for_new_runs",
                {"known_run_ids": ["run-001", "run-002", "run-003"], "timeout_s": 0.1},
            )
            elapsed = time.monotonic() - started

        assert elapsed < 2.0
        assert result.data == {"timed_out": True}


class TestRaiseAlert:
    async def test_writes_quarantine_file(self, small_campaign: tuple[Path, Path]) -> None:
        db_path, data_dir = small_campaign
        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool(
                "raise_alert",
                {
                    "run_id": "run-003",
                    "reason": "calibration drift confirmed via diff_runs",
                    "data_dir": str(data_dir),
                },
            )

        data = result.data
        assert data["quarantined"] is True
        assert data["run_id"] == "run-003"
        assert "calibration drift" in data["reason"]

        quarantine_path = data_dir / "QUARANTINE"
        assert quarantine_path.exists()
        content = quarantine_path.read_text(encoding="utf-8")
        assert "run-003" in content
        assert "calibration drift confirmed" in content


class TestLiftQuarantine:
    async def test_raise_then_lift_removes_sentinel(
        self, small_campaign: tuple[Path, Path]
    ) -> None:
        db_path, data_dir = small_campaign
        server = create_server(db_path)
        quarantine_path = data_dir / "QUARANTINE"

        async with Client(server) as client:
            await client.call_tool(
                "raise_alert",
                {"run_id": "run-003", "reason": "false alarm", "data_dir": str(data_dir)},
            )
            assert quarantine_path.exists()

            result = await client.call_tool("lift_quarantine", {"data_dir": str(data_dir)})

        assert result.data["lifted"] is True
        assert not quarantine_path.exists()

    async def test_lift_with_no_sentinel_reports_nothing_lifted(
        self, small_campaign: tuple[Path, Path]
    ) -> None:
        db_path, data_dir = small_campaign
        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool("lift_quarantine", {"data_dir": str(data_dir)})
        assert result.data["lifted"] is False
