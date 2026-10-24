"""Pytest fixtures for the data-onboarding tests (helpers live in onboarding_fixtures)."""

from __future__ import annotations

from pathlib import Path

import pytest
from onboarding_fixtures import build_bundle


@pytest.fixture()
def bundle(tmp_path: Path) -> Path:
    """A fresh synthetic bundle per test."""

    return build_bundle(tmp_path / "bundle")
