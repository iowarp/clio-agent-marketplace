"""The pack validates against clio-agent's real install-time blueprint validator.

Needs clio-agent importable (it is never a silent skip)::

    uv run --prerelease=allow --with "clio-agent @ git+https://github.com/iowarp/clio-agent@develop" \\
        --with "numpy>=1.24" --with "jsonschema>=4.18" --with trimesh --with pytest pytest appl-core/tests
"""

from __future__ import annotations

import pytest
from conftest import PACK


def _floor() -> str:
    from clio_agent.gact.agent_blueprints import parse_agent_blueprint_root

    return str(
        parse_agent_blueprint_root(PACK, scope="session").metadata["requires"][
            "clio_agent"
        ]
    )


def test_pack_blueprint_validates_against_the_real_validator() -> None:
    try:
        import clio_agent
        from clio_agent.gact.agent_blueprints import validate_agent_blueprint_path
    except ImportError as exc:  # pragma: no cover - not swallowed
        pytest.fail(f"clio_agent is not importable in this interpreter: {exc!r}")
    from packaging.specifiers import SpecifierSet
    from packaging.version import Version

    result = validate_agent_blueprint_path(PACK, scope="session")
    floor = _floor()
    running = clio_agent.__version__
    if Version(running) in SpecifierSet(floor):
        assert result["validation_errors"] == []
        assert result["enabled"] is True
    else:
        assert result["validation_errors"] == [
            f"appl-core: blueprint_requires_newer_clio_agent: requires clio_agent{floor}, running {running}"
        ]


def test_every_declared_skill_resolves_and_the_spawn_effect_parses() -> None:
    from clio_agent.gact.agent_blueprints import load_agent_blueprint_path
    from clio_agent.gact.agents.skill_effects import (
        EFFECT_SPAWN_SUBAGENT,
        parse_skill_effect,
    )
    from clio_agent.gact.skills import _parse_skill_frontmatter

    (main,) = [row for row in load_agent_blueprint_path(PACK) if row.id == "main"]
    assert main.enabled, main.validation_errors
    resolution = main.metadata["skill_resolution"]
    assert {skill: row["status"] for skill, row in resolution.items()} == {
        skill: "resolved" for skill in main.skills
    }

    for skill_md in sorted((PACK / "skills").glob("*/SKILL.md")):
        meta, body = _parse_skill_frontmatter(skill_md.read_text(encoding="utf-8"))
        assert meta["name"] == skill_md.parent.name
        assert body
        levels = [k for k in meta["keywords"] if k.startswith("level:")]
        assert len(levels) == 1, skill_md
        effect = parse_skill_effect(meta)
        if skill_md.parent.name == "audit-dataset":
            assert effect is not None and effect.kind == EFFECT_SPAWN_SUBAGENT
        else:
            assert effect is None, skill_md


def test_validation_has_no_warnings() -> None:
    from clio_agent.gact.agent_blueprints import validate_agent_blueprint_path

    assert (
        validate_agent_blueprint_path(PACK, scope="session")["validation_warnings"]
        == []
    )
