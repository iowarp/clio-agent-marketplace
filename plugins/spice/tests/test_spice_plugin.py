"""The spice plugin follows the SPICE connector and its skill keeps the person in charge."""

from __future__ import annotations

import json
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]


def test_it_follows_the_spice_connector() -> None:
    manifest = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
    clio = manifest["extensions"]["ai.iowarp.clio"]
    assert clio["follows"] == "spice" and clio["connections"] == {"spice": "spice"}


def test_installing_asks_the_person_and_can_be_skipped() -> None:
    text = (PLUGIN / "skills" / "install-simulator" / "SKILL.md").read_text(encoding="utf-8")
    assert "ask_user" in text and "skip simulation" in text
    for system in ("macOS", "Windows", "Linux"):
        assert system in text
    assert "never takes a password" in text
