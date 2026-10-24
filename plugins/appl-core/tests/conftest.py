"""Pytest fixtures for the appl-core tests (helpers live in appl_core_fixtures)."""

from __future__ import annotations

from pathlib import Path

import pytest
from appl_core_fixtures import build_bundle


@pytest.fixture()
def bundle(tmp_path: Path) -> Path:
    """A fresh synthetic bundle per test."""

    return build_bundle(tmp_path / "bundle")
