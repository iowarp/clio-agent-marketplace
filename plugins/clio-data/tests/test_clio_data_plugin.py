"""Layout contract for the clio-data plugin: mission first, levels, no subagents."""

from __future__ import annotations

import json
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
PROMPT = PLUGIN / "ai.iowarp.clio" / "prompt"


def _body(path: Path) -> str:
    return path.read_text(encoding="utf-8").split("---", 2)[2].strip()


def test_the_mission_is_the_only_fragment_and_fits_the_budget() -> None:
    assert [p.name for p in sorted(PROMPT.rglob("*.md"))] == ["mission.md"]
    assert (len(_body(PROMPT / "mission.md")) + 3) // 4 <= 150


def test_the_mission_names_skills_that_the_agent_carries() -> None:
    mission = _body(PROMPT / "mission.md")
    shipped = {
        p.parent.name
        for plugin in ("clio-data", "hdf5", "adios", "parquet")
        for p in (PLUGIN.parent / plugin / "skills").glob("*/SKILL.md")
    }
    named = {
        n for n in re.findall(r"`([a-z0-9-]+)`", mission) if not n.startswith(("shell", "create"))
    }
    assert named and named <= shipped


def test_skills_have_levels_and_no_subagents_ship() -> None:
    skills = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
    assert [p.parent.name for p in skills] == ["assess-data-quality", "convert-scientific-data"]
    for skill in skills:
        head = skill.read_text(encoding="utf-8").split("---", 2)[1]
        assert re.findall(r"(?m)^- (level:L[0-3])$", head) == ["level:L2"]
    assert not (PLUGIN / "ai.iowarp.clio" / "subagents").exists()


def test_requires_the_format_plugins_and_lint_files_exist() -> None:
    manifest = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
    requires = manifest["extensions"]["ai.iowarp.clio"]["requires"]
    assert set(requires) == {"data-onboarding", "hdf5", "adios", "parquet"}
    assert (PLUGIN / ".lint-l3").is_file() and (PLUGIN / "lint-denylist.txt").is_file()


def test_the_skill_documents_every_script_option() -> None:
    skill = (PLUGIN / "skills" / "convert-scientific-data" / "SKILL.md").read_text(encoding="utf-8")
    script = (
        PLUGIN / "skills" / "convert-scientific-data" / "scripts" / "convert_to_parquet.py"
    ).read_text(encoding="utf-8")
    options = set(re.findall(r'add_argument\(\s*"(--[a-z-]+)"', script))
    options |= set(re.findall(r'add_argument\("-o", "(--[a-z-]+)"', script))
    for option in options - {"--output"}:
        assert option in skill, option
