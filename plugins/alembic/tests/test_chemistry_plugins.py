"""The chemistry plugins: each follows its connector or server, every skill a step names
exists, and the install skills keep the person in charge."""

from __future__ import annotations

import json
import re
from pathlib import Path

PLUGINS = Path(__file__).resolve().parents[2]
FOLLOWERS = ("ase", "fdmnes", "graspa", "burette", "avogadro")
SERVERS = ("pubchem", "decimer")
CHEMISTRY = (*FOLLOWERS, *SERVERS, "computational-chemistry", "nwchem", "orca", "alembic")


def _manifest(name: str) -> dict:
    return json.loads((PLUGINS / name / "plugin.json").read_text(encoding="utf-8"))


def _skills() -> dict[str, str]:
    return {
        p.parent.name: " ".join(p.read_text(encoding="utf-8").split())
        for name in CHEMISTRY
        for p in (PLUGINS / name / "skills").glob("*/SKILL.md")
    }


def test_connector_plugins_follow_their_connector() -> None:
    for name in FOLLOWERS:
        clio = _manifest(name)["extensions"]["ai.iowarp.clio"]
        assert clio == {"follows": name, "connections": {name: name}}, name


def test_server_plugins_start_their_clio_kit_server() -> None:
    for name in SERVERS:
        mcp = json.loads((PLUGINS / name / "mcp.json").read_text(encoding="utf-8"))
        assert mcp["mcpServers"] == {
            name: {"type": "stdio", "command": "clio-kit", "args": ["mcp-server", name]}
        }


def test_every_plugin_is_held_to_the_level_contract() -> None:
    for name in CHEMISTRY:
        assert (PLUGINS / name / ".lint-l3").is_file(), name
        assert (PLUGINS / name / "lint-denylist.txt").is_file(), name


def test_skills_named_in_backticks_exist() -> None:
    skills = _skills()
    named = {
        m for text in skills.values() for m in re.findall(r"`([a-z]+(?:-[a-z]+)+)`", text)
    }
    referenced = {n for n in named if n.count("-") >= 1 and n in skills or n.startswith(
        ("method-", "geometry-", "pubchem-", "structure-", "install-", "fdmnes-", "graspa-", "xanes", "adsorption"))}
    assert referenced <= set(skills), referenced - set(skills)


def test_installs_ask_the_person_first_and_never_bypass() -> None:
    skills = _skills()
    for name in ("install-fdmnes", "install-graspa", "install-nwchem", "install-orca",
                 "install-avogadro"):
        assert "ask_user" in skills[name], name
    assert "do not bypass the checksum" in skills["install-fdmnes"]
    assert "never download ORCA" in skills["install-orca"]


def test_mission_is_main_only_and_short() -> None:
    text = (PLUGINS / "alembic" / "ai.iowarp.clio" / "prompt" / "mission.md").read_text()
    head, body = text.split("---", 2)[1:]
    assert 'when: {"tools": ["spawn_skill_task"]}' in head
    assert len(body.split()) <= 110  # about 150 tokens


def test_the_agent_composes_every_chemistry_plugin() -> None:
    agent = (PLUGINS.parent / "agents" / "alembic.py").read_text(encoding="utf-8")
    for name in CHEMISTRY:
        assert f'"{name}"' in agent, name
    assert "vina" not in agent and "docking" not in agent  # deferred
