"""Contract tests for the FastMCP "phenotype-workload" tool server: running
campaigns in-process, run-numbering continuation across invocations, the
invisible fault.json tamper mechanism, quarantine halting/lifting, and
campaign_status.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastmcp import Client

from spotter_ai.pipeline import stages
from spotter_ai.provenance.store import ProvenanceStore
from spotter_ai.quarantine import write_quarantine
from spotter_ai.workload import create_server


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "provenance.sqlite"


class TestRunCampaignBasic:
    async def test_produces_runs_and_provenance(self, tmp_path: Path, db_path: Path) -> None:
        server = create_server(db_path)
        data_dir = tmp_path / "campaign_data"
        payload = {"runs": 3, "campaign": "test-camp", "data_dir": str(data_dir), "sleep_s": 0}
        async with Client(server) as client:
            result = await client.call_tool("run_campaign", payload)

        data = result.data
        assert data["status"] == "completed"
        assert data["campaign"] == "test-camp"
        assert [r["run_id"] for r in data["runs"]] == ["run-001", "run-002", "run-003"]
        for entry in data["runs"]:
            assert set(entry) == {"run_id", "mean_biomass"}
            assert entry["mean_biomass"] > 0
        assert data["summary"]["run_count"] == 3
        assert data["summary"]["mean_biomass_avg"] > 0

        store = ProvenanceStore(db_path)
        runs = store.list_runs(campaign="test-camp")
        assert len(runs) == 3
        assert all(r["status"] == "completed" for r in runs)
        assert all(r["stage_count"] == 5 for r in runs)

    async def test_numbering_continues_across_invocations(
        self, tmp_path: Path, db_path: Path
    ) -> None:
        server = create_server(db_path)
        data_dir = tmp_path / "campaign_data"
        payload = {"runs": 2, "data_dir": str(data_dir), "sleep_s": 0}
        async with Client(server) as client:
            first = await client.call_tool("run_campaign", payload)
            assert [r["run_id"] for r in first.data["runs"]] == ["run-001", "run-002"]

            second = await client.call_tool("run_campaign", payload)
            assert [r["run_id"] for r in second.data["runs"]] == ["run-003", "run-004"]

    async def test_defaults_present_in_schema(self, tmp_path: Path, db_path: Path) -> None:
        server = create_server(db_path)
        async with Client(server) as client:
            tools = await client.list_tools()
        run_campaign_tool = next(t for t in tools if t.name == "run_campaign")
        schema_props = run_campaign_tool.inputSchema["properties"]
        assert schema_props["runs"]["default"] == 14
        assert schema_props["campaign"]["default"] == "phenotype-2026"
        assert schema_props["sleep_s"]["default"] == 2.0
        # No tamper parameter is exposed -- the fault mechanism is out-of-band.
        assert "tamper_at" not in schema_props
        assert "tamper" not in schema_props


class TestFaultInjection:
    """Proves the fault.json indexing semantics documented on run_campaign:
    tamper_at matches the 1-based index *within the calling invocation's own
    loop*, not the run's global run-NNN number, and none of it leaks into the
    tool's return value.
    """

    async def test_fault_matches_local_invocation_index_not_global(
        self, tmp_path: Path, db_path: Path
    ) -> None:
        server = create_server(db_path)
        data_dir = tmp_path / "campaign_data"
        data_dir.mkdir(parents=True)

        # First invocation: 10 healthy runs (run-001..run-010), no fault.json.
        async with Client(server) as client:
            first = await client.call_tool(
                "run_campaign", {"runs": 10, "data_dir": str(data_dir), "sleep_s": 0}
            )
        assert [r["run_id"] for r in first.data["runs"]] == [f"run-{i:03d}" for i in range(1, 11)]

        # Plant a fault for "the 2nd run of the NEXT invocation" -- if this
        # matched the global run number instead, it would hit nothing (run-2
        # already ran healthy) or the wrong run.
        (data_dir / "fault.json").write_text(json.dumps({"tamper_at": 2}), encoding="utf-8")

        async with Client(server) as client:
            second = await client.call_tool(
                "run_campaign", {"runs": 5, "data_dir": str(data_dir), "sleep_s": 0}
            )

        run_ids = [r["run_id"] for r in second.data["runs"]]
        assert run_ids == ["run-011", "run-012", "run-013", "run-014", "run-015"]

        # Invisibility: nothing in the returned payload mentions the fault.
        payload_text = json.dumps(second.data).lower()
        assert "tamper" not in payload_text
        assert "fault" not in payload_text
        assert second.data["status"] == "completed"

        # fault.json is left in place -- it's the demo's ground-truth record.
        assert (data_dir / "fault.json").exists()

        # Calibration was restored immediately after the tampered run.
        calibration = stages.read_json(data_dir / "calibration.json")
        assert calibration["scale_factor"] == pytest.approx(1.02)

        # Forensic ground truth (via the provenance store directly, standing
        # in for the separate "spotter" server): run-012 -- the *second* run
        # of the second invocation -- is the anomaly; its neighbors are not.
        store = ProvenanceStore(db_path)
        health_012 = store.get_run_health("run-012")
        biomass_012 = next(h for h in health_012 if h["metric"] == "mean_biomass")
        assert biomass_012["z"] > 5, f"expected run-012 z > 5, got {biomass_012['z']:.2f}"
        assert biomass_012["verdict"] == "anomalous"

        for healthy_run_id in ("run-011", "run-013"):
            health = store.get_run_health(healthy_run_id)
            biomass = next(h for h in health if h["metric"] == "mean_biomass")
            assert abs(biomass["z"]) < 3, f"{healthy_run_id} z={biomass['z']:.2f}"

        diff = store.diff_stage_executions("run-012", "run-011")
        assert diff["discrepancies"], "expected forensic evidence of the tamper"
        assert all(d["stage"] == "calibrate" for d in diff["discrepancies"])

    @staticmethod
    def _assert_calibrate_untampered(store: ProvenanceStore, run_id: str) -> None:
        """Assert a run's own recorded calibrate-stage params show no tamper.

        Checking the stored ``scale_factor`` directly is the ground truth for
        "was this run tampered" -- unlike a z-score, it doesn't need a
        reasonably sized baseline population to be reliable, so it works even
        for the small (3-5 run) campaigns these tests use.
        """
        executions = store.list_stage_executions(run_id, stage="calibrate")
        assert executions, f"no calibrate stage recorded for {run_id}"
        assert executions[0]["params"]["scale_factor"] == pytest.approx(1.02)

    async def test_no_fault_json_means_no_tamper(self, tmp_path: Path, db_path: Path) -> None:
        server = create_server(db_path)
        data_dir = tmp_path / "campaign_data"
        payload = {"runs": 5, "data_dir": str(data_dir), "sleep_s": 0}
        async with Client(server) as client:
            result = await client.call_tool("run_campaign", payload)

        store = ProvenanceStore(db_path)
        for entry in result.data["runs"]:
            self._assert_calibrate_untampered(store, entry["run_id"])

    async def test_malformed_fault_json_is_ignored(self, tmp_path: Path, db_path: Path) -> None:
        server = create_server(db_path)
        data_dir = tmp_path / "campaign_data"
        data_dir.mkdir(parents=True)
        (data_dir / "fault.json").write_text("not valid json {{{", encoding="utf-8")

        async with Client(server) as client:
            result = await client.call_tool(
                "run_campaign", {"runs": 3, "data_dir": str(data_dir), "sleep_s": 0}
            )

        assert result.data["status"] == "completed"
        store = ProvenanceStore(db_path)
        for entry in result.data["runs"]:
            self._assert_calibrate_untampered(store, entry["run_id"])


class TestQuarantine:
    async def test_halts_with_marked_status_before_first_run(
        self, tmp_path: Path, db_path: Path
    ) -> None:
        server = create_server(db_path)
        data_dir = tmp_path / "campaign_data"
        data_dir.mkdir(parents=True)
        write_quarantine(data_dir, run_id="run-003", reason="tampering detected")

        async with Client(server) as client:
            result = await client.call_tool(
                "run_campaign", {"runs": 5, "data_dir": str(data_dir), "sleep_s": 0}
            )

        data = result.data
        assert data["status"] == "halted"
        assert "SPOTTER AI" in data["message"]
        assert "tampering detected" in data["message"]
        assert data["runs"] == []
        assert data["summary"]["run_count"] == 0

    async def test_halts_before_next_run_in_a_continued_invocation(
        self, tmp_path: Path, db_path: Path
    ) -> None:
        server = create_server(db_path)
        data_dir = tmp_path / "campaign_data"
        payload = {"runs": 2, "data_dir": str(data_dir), "sleep_s": 0}
        async with Client(server) as client:
            first = await client.call_tool("run_campaign", payload)
        assert first.data["status"] == "completed"

        write_quarantine(data_dir, run_id="run-003", reason="stop")

        async with Client(server) as client:
            second = await client.call_tool(
                "run_campaign", {"runs": 3, "data_dir": str(data_dir), "sleep_s": 0}
            )
        assert second.data["status"] == "halted"
        assert second.data["runs"] == []

    async def test_lift_quarantine_removes_sentinel(self, tmp_path: Path, db_path: Path) -> None:
        server = create_server(db_path)
        data_dir = tmp_path / "campaign_data"
        data_dir.mkdir(parents=True)
        write_quarantine(data_dir, run_id="run-003", reason="x")
        assert (data_dir / "QUARANTINE").exists()

        async with Client(server) as client:
            result = await client.call_tool("lift_quarantine", {"data_dir": str(data_dir)})
        assert result.data["lifted"] is True
        assert not (data_dir / "QUARANTINE").exists()

        async with Client(server) as client:
            second = await client.call_tool("lift_quarantine", {"data_dir": str(data_dir)})
        assert second.data["lifted"] is False

    async def test_lift_quarantine_then_run_campaign_resumes(
        self, tmp_path: Path, db_path: Path
    ) -> None:
        server = create_server(db_path)
        data_dir = tmp_path / "campaign_data"
        data_dir.mkdir(parents=True)
        write_quarantine(data_dir, run_id="run-001", reason="paused")

        async with Client(server) as client:
            halted = await client.call_tool(
                "run_campaign", {"runs": 2, "data_dir": str(data_dir), "sleep_s": 0}
            )
            assert halted.data["status"] == "halted"

            await client.call_tool("lift_quarantine", {"data_dir": str(data_dir)})

            resumed = await client.call_tool(
                "run_campaign", {"runs": 2, "data_dir": str(data_dir), "sleep_s": 0}
            )

        assert resumed.data["status"] == "completed"
        assert [r["run_id"] for r in resumed.data["runs"]] == ["run-001", "run-002"]


class TestCampaignStatus:
    async def test_shape(self, tmp_path: Path, db_path: Path) -> None:
        server = create_server(db_path)
        data_dir = tmp_path / "campaign_data"
        async with Client(server) as client:
            await client.call_tool(
                "run_campaign", {"runs": 3, "data_dir": str(data_dir), "sleep_s": 0}
            )
            result = await client.call_tool("campaign_status", {"data_dir": str(data_dir)})

        data = result.data
        assert set(data) == {"data_dir", "runs", "run_count", "quarantined"}
        assert data["run_count"] == 3
        assert data["quarantined"] is False
        for run in data["runs"]:
            assert set(run) == {"run_id", "status", "metrics"}
            assert run["status"] == "completed"
            assert run["metrics"]["mean_biomass"] > 0

    async def test_reflects_quarantine(self, tmp_path: Path, db_path: Path) -> None:
        server = create_server(db_path)
        data_dir = tmp_path / "campaign_data"
        data_dir.mkdir(parents=True)
        write_quarantine(data_dir, "run-001", "test")

        async with Client(server) as client:
            result = await client.call_tool("campaign_status", {"data_dir": str(data_dir)})
        assert result.data["quarantined"] is True

    async def test_empty_data_dir(self, tmp_path: Path, db_path: Path) -> None:
        server = create_server(db_path)
        data_dir = tmp_path / "campaign_data"
        async with Client(server) as client:
            result = await client.call_tool("campaign_status", {"data_dir": str(data_dir)})
        assert result.data["run_count"] == 0
        assert result.data["runs"] == []
        assert result.data["quarantined"] is False
