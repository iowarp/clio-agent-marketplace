"""The wildfire skills are L1 methods with no run literals."""

from __future__ import annotations

import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]


def test_skills_are_l1_and_named_for_their_folder() -> None:
    skills = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
    assert {p.parent.name for p in skills} == {"fire-perimeters", "fire-risk-and-fuels"}
    for skill in skills:
        head = skill.read_text(encoding="utf-8").split("---", 2)[1]
        assert re.search(rf"(?m)^name: {skill.parent.name}$", head)
        assert re.findall(r"(?m)^- level:(L[0-3])$", head) == ["L1"]
