"""Contract tests for the FastMCP "phenotype-workload" tool server: running
measurement batches in-process, run-numbering continuation across
invocations, the invisible fault.json tamper mechanism, quarantine
halting/lifting, campaign_status, server-side campaign/data-dir config
resolution, and per-batch report artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastmcp import Client

from spotter_ai.config import DEFAULT_CAMPAIGN_NAME
from spotter_ai.pipeline import stages
from spotter_ai.provenance.store import ProvenanceStore
from spotter_ai.quarantine import write_quarantine
from spotter_ai.reports import REPORT_METRICS
from spotter_ai.workload import create_server


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "provenance.sqlite"


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point SPOTTER_DATA_DIR at an isolated directory under tmp_path.

    Campaign name and data directory are server-side config, resolved once
    when create_server() builds the server (see spotter_ai.config) -- so the
    env var must be set BEFORE create_server() is called in each test.
    """
    d = tmp_path / "campaign_data"
    monkeypatch.setenv("SPOTTER_DATA_DIR", str(d))
    return d


class TestMeasureCohortBasic:
    async def test_produces_runs_and_provenance(
        self, tmp_path: Path, db_path: Path, data_dir: Path
    ) -> None:
        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool("measure_cohort", {"runs": 3, "pace_seconds": 0})

        data = result.data
        assert data["status"] == "completed"
        assert data["campaign"] == DEFAULT_CAMPAIGN_NAME
        assert [r["run_id"] for r in data["runs"]] == ["run-001", "run-002", "run-003"]
        for entry in data["runs"]:
            assert set(entry) == {"run_id", "mean_biomass"}
            assert entry["mean_biomass"] > 0
        assert data["summary"]["run_count"] == 3
        assert data["summary"]["mean_biomass_avg"] > 0
        assert data["written_path"] is not None

        store = ProvenanceStore(db_path)
        runs = store.list_runs(campaign=DEFAULT_CAMPAIGN_NAME)
        assert len(runs) == 3
        assert all(r["status"] == "completed" for r in runs)
        assert all(r["stage_count"] == 5 for r in runs)

    async def test_numbering_continues_across_invocations(
        self, tmp_path: Path, db_path: Path, data_dir: Path
    ) -> None:
        server = create_server(db_path)
        payload = {"runs": 2, "pace_seconds": 0}
        async with Client(server) as client:
            first = await client.call_tool("measure_cohort", payload)
            assert [r["run_id"] for r in first.data["runs"]] == ["run-001", "run-002"]

            second = await client.call_tool("measure_cohort", payload)
            assert [r["run_id"] for r in second.data["runs"]] == ["run-003", "run-004"]

    async def test_defaults_present_in_schema(self, db_path: Path, data_dir: Path) -> None:
        server = create_server(db_path)
        async with Client(server) as client:
            tools = await client.list_tools()
        measure_cohort_tool = next(t for t in tools if t.name == "measure_cohort")
        schema_props = measure_cohort_tool.inputSchema["properties"]

        # ONLY the two per-call arguments are exposed -- campaign and
        # data_dir are server-side config now, never model-supplied.
        assert set(schema_props) == {"runs", "pace_seconds"}
        assert schema_props["runs"]["default"] == 14
        assert schema_props["pace_seconds"]["default"] == 10.0
        # No tamper parameter is exposed -- the fault mechanism is out-of-band.
        assert "tamper_at" not in schema_props
        assert "tamper" not in schema_props

    async def test_other_tools_also_drop_campaign_and_data_dir(
        self, db_path: Path, data_dir: Path
    ) -> None:
        server = create_server(db_path)
        async with Client(server) as client:
            tools = await client.list_tools()
        by_name = {t.name: set(t.inputSchema.get("properties", {})) for t in tools}
        assert by_name == {
            "measure_cohort": {"runs", "pace_seconds"},
            "campaign_status": set(),
            "lift_quarantine": set(),
        }

    async def test_campaign_env_override_is_used(
        self, tmp_path: Path, db_path: Path, data_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SPOTTER_CAMPAIGN, when set, is used instead of the default -- resolved
        once at server construction, per spotter_ai.config.
        """
        monkeypatch.setenv("SPOTTER_CAMPAIGN", "owner-review-2026")
        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool("measure_cohort", {"runs": 1, "pace_seconds": 0})

        assert result.data["campaign"] == "owner-review-2026"
        store = ProvenanceStore(db_path)
        assert len(store.list_runs(campaign="owner-review-2026")) == 1
        assert store.list_runs(campaign=DEFAULT_CAMPAIGN_NAME) == []

    async def test_campaign_defaults_when_env_unset(
        self, db_path: Path, data_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SPOTTER_CAMPAIGN", raising=False)
        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool("measure_cohort", {"runs": 1, "pace_seconds": 0})
        assert result.data["campaign"] == DEFAULT_CAMPAIGN_NAME

    async def test_data_dir_env_determines_where_runs_land(
        self, tmp_path: Path, db_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        custom_dir = tmp_path / "somewhere-else"
        monkeypatch.setenv("SPOTTER_DATA_DIR", str(custom_dir))
        server = create_server(db_path)
        async with Client(server) as client:
            await client.call_tool("measure_cohort", {"runs": 1, "pace_seconds": 0})

        assert (custom_dir / "runs" / "run-001").exists()
        assert not (Path("./campaign_data") / "runs").exists()

    async def test_data_dir_defaults_to_cwd_relative_campaign_data(
        self, tmp_path: Path, db_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SPOTTER_DATA_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        server = create_server(db_path)
        async with Client(server) as client:
            await client.call_tool("measure_cohort", {"runs": 1, "pace_seconds": 0})

        assert (tmp_path / "campaign_data" / "runs" / "run-001").exists()


class TestFaultInjection:
    """Proves the fault.json indexing semantics documented on measure_cohort:
    tamper_at matches the run's GLOBAL run-NNN number -- the same number
    embedded in its run_id -- regardless of which measure_cohort call actually
    produces that run, and none of it leaks into the tool's return value.

    The demo drives a campaign as a sequence of smaller batched calls (e.g.
    runs=8, then runs=6, ...), so a per-call-local index could never target
    a run past the size of a single call. Global indexing is what lets a
    demo operator plan "tamper run 12" up front.
    """

    async def test_fault_matches_global_run_number_across_batched_calls(
        self, tmp_path: Path, db_path: Path, data_dir: Path
    ) -> None:
        server = create_server(db_path)
        data_dir.mkdir(parents=True)

        # Plant a fault for global run-012 *before either call* -- a
        # per-invocation-local index could never reach "12" from an 8-run
        # first call or a 6-run second call.
        (data_dir / "fault.json").write_text(json.dumps({"tamper_at": 12}), encoding="utf-8")

        # First call: 8 healthy runs (run-001..run-008). No local index in
        # this call ever equals 12, so nothing should be tampered here.
        async with Client(server) as client:
            first = await client.call_tool("measure_cohort", {"runs": 8, "pace_seconds": 0})
        assert [r["run_id"] for r in first.data["runs"]] == [f"run-{i:03d}" for i in range(1, 9)]
        assert first.data["status"] == "completed"

        # Second call: 6 more runs (run-009..run-014). Global run-012 falls
        # inside this call, at its *5th* local iteration.
        async with Client(server) as client:
            second = await client.call_tool("measure_cohort", {"runs": 6, "pace_seconds": 0})

        run_ids = [r["run_id"] for r in second.data["runs"]]
        assert run_ids == [f"run-{i:03d}" for i in range(9, 15)]
        assert second.data["status"] == "completed"

        # Invisibility: nothing in either call's returned payload mentions
        # the fault, in either call (written_path is a filesystem path, not
        # payload content, so it is excluded from this text scan).
        for payload in (first.data, second.data):
            payload_text = json.dumps({k: v for k, v in payload.items() if k != "written_path"})
            payload_text = payload_text.lower()
            assert "tamper" not in payload_text
            assert "fault" not in payload_text

        # fault.json is left in place -- it's the demo's ground-truth record.
        assert (data_dir / "fault.json").exists()

        # Calibration was restored immediately after the tampered run.
        calibration = stages.read_json(data_dir / "calibration.json")
        assert calibration["scale_factor"] == pytest.approx(1.02)

        # Forensic ground truth (via the provenance store directly, standing
        # in for the separate "spotter" server): run-012 is the anomaly;
        # its neighbors -- including run-008, the last run of the FIRST
        # call, proving the first call was untouched -- are not.
        store = ProvenanceStore(db_path)
        health_012 = store.get_run_health("run-012")
        biomass_012 = next(h for h in health_012 if h["metric"] == "mean_biomass")
        assert biomass_012["z"] > 5, f"expected run-012 z > 5, got {biomass_012['z']:.2f}"
        assert biomass_012["verdict"] == "anomalous"

        for healthy_run_id in ("run-008", "run-011", "run-013"):
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

    async def test_no_fault_json_means_no_tamper(
        self, tmp_path: Path, db_path: Path, data_dir: Path
    ) -> None:
        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool("measure_cohort", {"runs": 5, "pace_seconds": 0})

        store = ProvenanceStore(db_path)
        for entry in result.data["runs"]:
            self._assert_calibrate_untampered(store, entry["run_id"])

    async def test_malformed_fault_json_is_ignored(
        self, tmp_path: Path, db_path: Path, data_dir: Path
    ) -> None:
        server = create_server(db_path)
        data_dir.mkdir(parents=True)
        (data_dir / "fault.json").write_text("not valid json {{{", encoding="utf-8")

        async with Client(server) as client:
            result = await client.call_tool("measure_cohort", {"runs": 3, "pace_seconds": 0})

        assert result.data["status"] == "completed"
        store = ProvenanceStore(db_path)
        for entry in result.data["runs"]:
            self._assert_calibrate_untampered(store, entry["run_id"])


class TestQuarantine:
    async def test_halts_with_marked_status_before_first_run(
        self, tmp_path: Path, db_path: Path, data_dir: Path
    ) -> None:
        server = create_server(db_path)
        data_dir.mkdir(parents=True)
        write_quarantine(data_dir, run_id="run-003", reason="tampering detected")

        async with Client(server) as client:
            result = await client.call_tool("measure_cohort", {"runs": 5, "pace_seconds": 0})

        data = result.data
        assert data["status"] == "halted"
        assert "SPOTTER AI" in data["message"]
        assert "tampering detected" in data["message"]
        assert data["runs"] == []
        assert data["summary"]["run_count"] == 0
        assert data["written_path"] is None

    async def test_halts_before_next_run_in_a_continued_invocation(
        self, tmp_path: Path, db_path: Path, data_dir: Path
    ) -> None:
        server = create_server(db_path)
        payload = {"runs": 2, "pace_seconds": 0}
        async with Client(server) as client:
            first = await client.call_tool("measure_cohort", payload)
        assert first.data["status"] == "completed"

        write_quarantine(data_dir, run_id="run-003", reason="stop")

        async with Client(server) as client:
            second = await client.call_tool("measure_cohort", {"runs": 3, "pace_seconds": 0})
        assert second.data["status"] == "halted"
        assert second.data["runs"] == []
        assert second.data["written_path"] is None

    async def test_lift_quarantine_removes_sentinel(
        self, tmp_path: Path, db_path: Path, data_dir: Path
    ) -> None:
        server = create_server(db_path)
        data_dir.mkdir(parents=True)
        write_quarantine(data_dir, run_id="run-003", reason="x")
        assert (data_dir / "QUARANTINE").exists()

        async with Client(server) as client:
            result = await client.call_tool("lift_quarantine", {})
        assert result.data["lifted"] is True
        assert not (data_dir / "QUARANTINE").exists()

        async with Client(server) as client:
            second = await client.call_tool("lift_quarantine", {})
        assert second.data["lifted"] is False

    async def test_lift_quarantine_then_measure_cohort_resumes(
        self, tmp_path: Path, db_path: Path, data_dir: Path
    ) -> None:
        server = create_server(db_path)
        data_dir.mkdir(parents=True)
        write_quarantine(data_dir, run_id="run-001", reason="paused")

        async with Client(server) as client:
            halted = await client.call_tool("measure_cohort", {"runs": 2, "pace_seconds": 0})
            assert halted.data["status"] == "halted"

            await client.call_tool("lift_quarantine", {})

            resumed = await client.call_tool("measure_cohort", {"runs": 2, "pace_seconds": 0})

        assert resumed.data["status"] == "completed"
        assert [r["run_id"] for r in resumed.data["runs"]] == ["run-001", "run-002"]


class TestCampaignStatus:
    async def test_shape(self, tmp_path: Path, db_path: Path, data_dir: Path) -> None:
        server = create_server(db_path)
        async with Client(server) as client:
            await client.call_tool("measure_cohort", {"runs": 3, "pace_seconds": 0})
            result = await client.call_tool("campaign_status", {})

        data = result.data
        assert set(data) == {"data_dir", "runs", "run_count", "quarantined"}
        assert data["run_count"] == 3
        assert data["quarantined"] is False
        for run in data["runs"]:
            assert set(run) == {"run_id", "status", "metrics"}
            assert run["status"] == "completed"
            assert run["metrics"]["mean_biomass"] > 0

    async def test_reflects_quarantine(self, tmp_path: Path, db_path: Path, data_dir: Path) -> None:
        server = create_server(db_path)
        data_dir.mkdir(parents=True)
        write_quarantine(data_dir, "run-001", "test")

        async with Client(server) as client:
            result = await client.call_tool("campaign_status", {})
        assert result.data["quarantined"] is True

    async def test_empty_data_dir(self, tmp_path: Path, db_path: Path, data_dir: Path) -> None:
        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool("campaign_status", {})
        assert result.data["run_count"] == 0
        assert result.data["runs"] == []
        assert result.data["quarantined"] is False


class TestBatchReport:
    """The per-batch report artifact measure_cohort writes under
    <data_dir>/reports/batch-NNN.json, and returns the path to as
    written_path (one of clio-agent's recognized result-path keys, so the
    platform auto-mints it) -- see spotter_ai.reports.
    """

    # Frozen copy of clio-agent's gact/artifacts/designation.py::RESULT_PATH_KEYS
    # (spotter-ai does not import clio_agent -- separate repos/venvs). The
    # platform's tool observer auto-registers a workspace artifact for any
    # top-level tool-result key in THIS exact set; "written_path" only
    # auto-mints because it is a member. If clio-agent's vocabulary ever
    # changes, this copy diverging is the signal to reconcile the two.
    _CLIO_AGENT_RESULT_PATH_KEYS = frozenset(
        {
            "local_path",
            "output_path",
            "output_file",
            "saved_path",
            "saved_to",
            "written_path",
            "result_path",
            "out_path",
        }
    )

    def test_written_path_is_in_clio_agents_recognized_result_path_vocabulary(self) -> None:
        assert "written_path" in self._CLIO_AGENT_RESULT_PATH_KEYS

    async def test_written_path_is_always_absolute(
        self, tmp_path: Path, db_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """#1218 r4 live-gate finding: written_path came back as
        "campaign_data\\reports\\batch-001.json" (relative, SPOTTER_DATA_DIR
        left at its relative default) and clio-agent's platform-side mint
        resolved that string against its OWN process's cwd -- not this MCP
        server's, and not the workspace root -- landing outside the
        workspace and getting silently rejected (containment_rejected,
        gact/artifacts/minting.py's _contained), so the artifact panel
        stayed empty despite 5/5 tool calls returning a path. Reproduces
        with SPOTTER_DATA_DIR explicitly set to a RELATIVE value (the
        reported shape) and pins that written_path is absolute regardless.
        """
        monkeypatch.setenv("SPOTTER_DATA_DIR", "./campaign_data")
        monkeypatch.chdir(tmp_path)
        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool("measure_cohort", {"runs": 1, "pace_seconds": 0})

        written_path = result.data["written_path"]
        assert written_path is not None
        assert Path(written_path).is_absolute(), (
            f"written_path must be absolute so a DIFFERENT process (the platform "
            f"server) can resolve it correctly; got {written_path!r}"
        )
        assert Path(written_path) == tmp_path / "campaign_data" / "reports" / "batch-001.json"

    async def test_report_written_with_pinned_shape(
        self, tmp_path: Path, db_path: Path, data_dir: Path
    ) -> None:
        server = create_server(db_path)
        async with Client(server) as client:
            result = await client.call_tool("measure_cohort", {"runs": 3, "pace_seconds": 0})

        report_path = Path(result.data["written_path"])
        assert report_path.exists()
        assert report_path.name == "batch-001.json"
        assert report_path.parent == data_dir / "reports"

        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert set(report) == {
            "batch_number",
            "campaign",
            "generated_at",
            "run_range",
            "runs",
            "batch_stats",
            "campaign_totals",
        }
        assert report["batch_number"] == 1
        assert report["campaign"] == DEFAULT_CAMPAIGN_NAME
        assert report["run_range"] == {"first": "run-001", "last": "run-003"}

        assert [r["run_id"] for r in report["runs"]] == ["run-001", "run-002", "run-003"]
        for run in report["runs"]:
            assert set(run) == {"run_id", *REPORT_METRICS}
            for metric in REPORT_METRICS:
                assert run[metric] > 0

        assert set(report["batch_stats"]) == set(REPORT_METRICS)
        for metric_stats in report["batch_stats"].values():
            assert set(metric_stats) == {"mean", "min", "max"}
            assert metric_stats["min"] <= metric_stats["mean"] <= metric_stats["max"]

        assert report["campaign_totals"]["run_count"] == 3
        for metric in REPORT_METRICS:
            assert report["campaign_totals"][f"{metric}_avg"] > 0

    async def test_second_batch_gets_next_number_and_cumulative_totals(
        self, tmp_path: Path, db_path: Path, data_dir: Path
    ) -> None:
        server = create_server(db_path)
        async with Client(server) as client:
            first = await client.call_tool("measure_cohort", {"runs": 2, "pace_seconds": 0})
            second = await client.call_tool("measure_cohort", {"runs": 3, "pace_seconds": 0})

        first_report = json.loads(Path(first.data["written_path"]).read_text(encoding="utf-8"))
        second_report = json.loads(Path(second.data["written_path"]).read_text(encoding="utf-8"))

        assert first_report["batch_number"] == 1
        assert second_report["batch_number"] == 2
        assert Path(second.data["written_path"]).name == "batch-002.json"

        # This batch's own table has only the 3 new runs...
        assert [r["run_id"] for r in second_report["runs"]] == ["run-003", "run-004", "run-005"]
        # ...but the campaign totals accumulate across both batches.
        assert second_report["campaign_totals"]["run_count"] == 5
        assert first_report["campaign_totals"]["run_count"] == 2

    async def test_no_report_when_halted_before_any_run(
        self, tmp_path: Path, db_path: Path, data_dir: Path
    ) -> None:
        server = create_server(db_path)
        data_dir.mkdir(parents=True)
        write_quarantine(data_dir, run_id="run-001", reason="halted immediately")

        async with Client(server) as client:
            result = await client.call_tool("measure_cohort", {"runs": 5, "pace_seconds": 0})

        assert result.data["status"] == "halted"
        assert result.data["written_path"] is None
        assert not (data_dir / "reports").exists()

    async def test_report_written_even_when_batch_halts_partway(
        self, tmp_path: Path, db_path: Path, data_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A quarantine sentinel dropped mid-batch (between two runs of the
        SAME call) still leaves a report for the runs that did complete
        before the halt -- status is "halted" but written_path is not None.
        """
        server = create_server(db_path)

        # Same technique test_pipeline.py's test_quarantine_halts_mid_campaign
        # uses: wrap run_single so the sentinel appears right after the 2nd
        # run of a 5-run call, forcing a halt with 2 completed runs in hand.
        import spotter_ai.workload as workload_module

        original_run_single = workload_module.campaign_module.run_single
        call_count = {"n": 0}

        def run_single_then_quarantine(*a: object, **kw: object) -> dict[str, float]:
            call_count["n"] += 1
            result = original_run_single(*a, **kw)
            if call_count["n"] == 2:
                write_quarantine(data_dir, run_id="run-003", reason="injected mid-batch")
            return result

        workload_module.campaign_module.run_single = run_single_then_quarantine
        try:
            async with Client(server) as client:
                result = await client.call_tool("measure_cohort", {"runs": 5, "pace_seconds": 0})
        finally:
            workload_module.campaign_module.run_single = original_run_single

        assert result.data["status"] == "halted"
        assert [r["run_id"] for r in result.data["runs"]] == ["run-001", "run-002"]

        report_path = result.data["written_path"]
        assert report_path is not None
        report = json.loads(Path(report_path).read_text(encoding="utf-8"))
        assert [r["run_id"] for r in report["runs"]] == ["run-001", "run-002"]
