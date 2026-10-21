"""Level contract for the appl-core plugin: skill levels and no L3 literals.

Dependency-free; runs with the plugin's other tests.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]

#: Each skill's level. L3 (one experiment) never ships in the plugin.
EXPECTED_LEVELS: dict[str, str] = {
    "onboard-dataset": "L0",
    "audit-dataset": "L0",
    "evidence-and-claims": "L0",
    "geometry-to-glb": "L0",
    "phenotyping-onboarding-checks": "L1",
    "size-and-growth-traits": "L1",
    "treatment-response": "L1",
    "physiology-signals": "L1",
    "phenotyping-report": "L1",
    "appl-core-exports": "L2",
    "appl-instruments": "L2",
}
L3_LITERALS = ("Weston", "2026.04.09", "OPAL.0002", "28773", "29014", "5577", "Thalpsi")


def _skill_dirs() -> list[Path]:
    return sorted(path.parent for path in (PLUGIN / "skills").glob("*/SKILL.md"))


def _head(skill_dir: Path) -> str:
    return (skill_dir / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]


def test_every_skill_has_the_expected_level() -> None:
    assert {path.name for path in _skill_dirs()} == set(EXPECTED_LEVELS)
    for skill_dir in _skill_dirs():
        head = _head(skill_dir)
        assert re.search(rf"(?m)^name: {re.escape(skill_dir.name)}$", head)
        assert re.findall(r"(?m)^- (level:L[0-3])$", head) == [
            f"level:{EXPECTED_LEVELS[skill_dir.name]}"
        ]
        assert re.search(r"^[ \t]+-[ \t]", head, re.MULTILINE) is None


def test_only_the_audit_skill_spawns_a_child() -> None:
    for skill_dir in _skill_dirs():
        effect = re.search(r"(?m)^effect: (\S+)$", _head(skill_dir))
        expected = "spawn_subagent_with_skill" if skill_dir.name == "audit-dataset" else None
        assert (effect.group(1) if effect else None) == expected


def test_lint_marker_and_denylist_are_present() -> None:
    assert (PLUGIN / ".lint-l3").is_file()
    literals = [
        line.strip()
        for line in (PLUGIN / "lint-denylist.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert sorted(literals) == sorted(L3_LITERALS)


@pytest.mark.parametrize("literal", L3_LITERALS)
def test_no_denylisted_literal_in_shipped_files(literal: str) -> None:
    shipped = [
        path
        for folder in (PLUGIN / "skills", PLUGIN / "ai.iowarp.clio")
        for path in sorted(folder.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    ]
    for path in shipped:
        text = path.read_text(encoding="utf-8", errors="replace").casefold()
        assert literal.casefold() not in text, path.relative_to(PLUGIN).as_posix()
