"""Layout contract for the earthscope plugin: mission first, one source skill, no literals."""

from __future__ import annotations

import json
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
PROMPT = PLUGIN / "ai.iowarp.clio" / "prompt"


def _denylist() -> list[str]:
    return [
        line.strip()
        for line in (PLUGIN / "lint-denylist.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def test_the_mission_sorts_first_and_fits_the_budget() -> None:
    fragments = sorted(PROMPT.glob("*.md"))
    assert [p.name for p in fragments] == ["mission.md", "views.md"]
    for fragment in fragments:
        body = fragment.read_text(encoding="utf-8").split("---", 2)[2].strip()
        assert (len(body) + 3) // 4 <= 150, fragment.name


def test_one_level_two_source_skill() -> None:
    skills = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
    assert [p.parent.name for p in skills] == ["acquire-earthscope-gnss"]
    head = skills[0].read_text(encoding="utf-8").split("---", 2)[1]
    assert re.findall(r"(?m)^- (level:L[0-3])$", head) == ["level:L2"]


def test_workflow_state_keeps_only_what_core_reads() -> None:
    manifest = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
    clio = manifest["extensions"]["ai.iowarp.clio"]
    assert set(clio["requires"]) == {"ndp", "geo", "geodesy"}
    assert "aliases" not in clio["workflow_state"]
    assert (
        clio["workflow_state"]["sections"]["acquisition"]["readiness"]["field"] == "analysis_ready"
    )


def test_no_denylisted_literal_anywhere_shipped() -> None:
    literals = _denylist()
    assert literals
    for path in sorted(PLUGIN.rglob("*")):
        if not path.is_file() or "tests" in path.parts or path.name == "lint-denylist.txt":
            continue
        if path.suffix not in {".md", ".json", ".py", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8")
        for literal in literals:
            assert literal not in text, (path.relative_to(PLUGIN).as_posix(), literal)
