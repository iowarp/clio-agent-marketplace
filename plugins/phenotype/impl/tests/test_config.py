"""Tests for phenotype_workload.config: campaign name, data directory, and provenance
database path resolution (#1218 r3: a split-brain db, empty and created inside
the campaign data directory, was observed when the historical default_db_path
fallback was resolved independently of resolve_data_dir).

Since the pack split, the SPOTTER forensic server lives in its own project
(``spotter-ai``) with its own config; the cross-pack same-database contract is
exercised at the pack boundary (live qualification), not in this suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastmcp import Client

from phenotype_workload import config
from phenotype_workload.workload import create_server as create_workload_server


class TestResolveCampaignName:
    def test_env_set_is_used(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SPOTTER_CAMPAIGN", "custom-campaign")
        assert config.resolve_campaign_name() == "custom-campaign"

    def test_env_unset_uses_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SPOTTER_CAMPAIGN", raising=False)
        assert config.resolve_campaign_name() == config.DEFAULT_CAMPAIGN_NAME


class TestResolveDataDir:
    def test_env_set_is_used(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SPOTTER_DATA_DIR", str(tmp_path / "somewhere"))
        assert config.resolve_data_dir() == tmp_path / "somewhere"

    def test_env_unset_uses_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SPOTTER_DATA_DIR", raising=False)
        assert config.resolve_data_dir() == Path(config.DEFAULT_DATA_DIR).resolve()

    def test_always_returns_an_absolute_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """#1218 r4: a relative data dir round-tripped into a tool result
        (measure_cohort's written_path) and got resolved by clio-agent
        against the WRONG process's cwd (the platform server's, not this
        MCP server's), silently failing the platform's containment check.
        resolve_data_dir must never return a relative path, regardless of
        source.
        """
        monkeypatch.setenv("SPOTTER_DATA_DIR", "./relative_campaign_data")
        monkeypatch.chdir(tmp_path)
        resolved = config.resolve_data_dir()
        assert resolved.is_absolute()
        assert resolved == tmp_path / "relative_campaign_data"

        monkeypatch.delenv("SPOTTER_DATA_DIR", raising=False)
        assert config.resolve_data_dir().is_absolute()


class TestResolveDbPath:
    """default_db_path used to be resolved via a bare cwd-relative literal,
    completely independent of resolve_data_dir's OWN, also cwd-relative,
    default -- two separate computations that could silently disagree
    whenever evaluated from different working directories. resolve_db_path
    now derives its fallback from resolve_data_dir's own resolution, so the
    two provably agree by construction.
    """

    def test_env_set_wins_and_is_absolute(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db_path = tmp_path / "custom.sqlite"
        monkeypatch.setenv("SPOTTER_DB", str(db_path))
        assert config.resolve_db_path() == db_path.resolve()

    def test_env_unset_lands_beside_data_dir_not_inside_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SPOTTER_DB", raising=False)
        monkeypatch.setenv("SPOTTER_DATA_DIR", str(tmp_path / "campaign_data"))
        resolved = config.resolve_db_path()
        assert resolved == tmp_path / config.DB_FILENAME
        assert resolved.parent == (tmp_path / "campaign_data").parent

    def test_env_unset_default_data_dir_resolves_relative_to_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With NEITHER env var set, both defaults are cwd-relative -- but
        now derived from the ONE resolve_data_dir() call, so they can no
        longer independently diverge the way #1218 r3's split-brain db did.
        """
        monkeypatch.delenv("SPOTTER_DB", raising=False)
        monkeypatch.delenv("SPOTTER_DATA_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        assert config.resolve_db_path() == tmp_path / config.DB_FILENAME

    async def test_a_campaign_leaves_exactly_one_db_file_with_tables(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """End-to-end regression for the split-brain db: running a real
        campaign through the workload server with db_path=None (exercising
        the SAME fallback the live demo used) must land on ONE file with the
        campaign's data -- never a second, empty stray database beside it.
        (The forensic-server read-back half of #1218 r3 now lives at the
        pack boundary: the spotter-ai project reads this same store.)
        """
        monkeypatch.delenv("SPOTTER_DB", raising=False)
        data_dir = tmp_path / "campaign_data"
        monkeypatch.setenv("SPOTTER_DATA_DIR", str(data_dir))

        workload_server = create_workload_server(None)
        async with Client(workload_server) as client:
            result = await client.call_tool("measure_cohort", {"runs": 3, "pace_seconds": 0})
        assert result.data["status"] == "completed"

        sqlite_files = sorted(tmp_path.rglob("*.sqlite"))
        assert len(sqlite_files) == 1, f"expected exactly one db file, found {sqlite_files}"
        db_file = sqlite_files[0]
        assert db_file == tmp_path / config.DB_FILENAME
        assert db_file.stat().st_size > 0
