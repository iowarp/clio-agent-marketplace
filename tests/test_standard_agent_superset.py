"""The domain agents are supersets of the standard agent (Base Agent).

Until packs become plugins layered on a base plugin, each domain agent carries
everything the standard agent has -- its tools, MCP servers, A2UI catalogs,
skills (including the clio built-ins the default agent gets automatically) and
working principles -- and adds its own domain on top. These tests read Base
Agent as the source, so a capability added there is required here too.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import Any

from tests.test_base_agent_policy import parse_frontmatter

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / "base-agent"

#: Domain agents that must stay supersets of the standard agent.
SUPERSET_PACKS = ("appl-core", "factorio-flat", "earthscope-single-agent")

#: clio built-in skills the default agent's root expert gets automatically
#: (clio-agent ``effective_declared_skills``); any other pack must declare them.
DEFAULT_AGENT_BUILTIN_SKILLS = frozenset(
    {
        "work-with-pdfs",
        "planning",
        "update-models",
        "present-interactive-analysis",
        "create-dashboard",
        "review-visual-presentation",
    }
)

#: A root expert with a declared A2UI catalog gets these four tools automatically,
#: so declaring them is a partial, redundant list.
A2UI_PRODUCER_TOOLS = frozenset(
    {
        "create_a2ui_surface",
        "update_a2ui_components",
        "update_a2ui_data_model",
        "delete_a2ui_surface",
    }
)


def _root_expert(pack: Path) -> dict[str, Any]:
    """Return the parsed frontmatter of ``pack``'s root expert."""

    manifest = parse_frontmatter(pack / "AGENT.md")
    root = manifest["root_expert"]
    for rel in manifest["experts"]:
        expert = parse_frontmatter(pack / rel)
        if expert["id"] == root:
            return expert
    raise AssertionError(f"{pack.name}: root expert {root!r} is not declared")


def _root_prompt(pack: Path) -> str:
    """Return ``pack``'s root expert prompt body (after the frontmatter)."""

    manifest = parse_frontmatter(pack / "AGENT.md")
    for rel in manifest["experts"]:
        text = (pack / rel).read_text(encoding="utf-8")
        if parse_frontmatter(pack / rel)["id"] == manifest["root_expert"]:
            return text.split("\n---", 2)[-1]
    raise AssertionError(f"{pack.name}: no root expert prompt")


def _server_command(server: Any) -> list[str]:
    """Normalize an MCP server declaration (string or mapping) to its argv."""

    if isinstance(server, str):
        return server.split()
    return [str(server["command"]), *[str(arg) for arg in server.get("args", [])]]


def _catalog_ids(entries: list[Any]) -> list[str]:
    """Catalog ids from an ``a2ui_catalogs`` list (plain ids or one-key mappings)."""

    ids: list[str] = []
    for entry in entries:
        ids.extend(entry if isinstance(entry, dict) else [entry])
    return [str(entry) for entry in ids]


def _principles(prompt: str) -> str:
    """The standard ``## Working principles`` section, whitespace-normalized."""

    match = re.search(r"## Working principles\n(.*?)(?=\n## |\nGive a clear|\Z)", prompt, re.S)
    if match is None:
        raise AssertionError("no '## Working principles' section")
    return " ".join(match.group(1).split())


class StandardAgentSupersetTests(unittest.TestCase):
    """Each domain agent has everything the standard agent has."""

    def setUp(self) -> None:
        self.base_manifest = parse_frontmatter(BASE / "AGENT.md")
        self.base_expert = _root_expert(BASE)

    def test_tools(self) -> None:
        for name in SUPERSET_PACKS:
            with self.subTest(pack=name):
                tools = set(_root_expert(REPO / name)["tools"])
                self.assertLessEqual(set(self.base_expert["tools"]), tools)
                self.assertEqual(tools & A2UI_PRODUCER_TOOLS, set())

    def test_mcp_servers(self) -> None:
        for name in SUPERSET_PACKS:
            with self.subTest(pack=name):
                servers = parse_frontmatter(REPO / name / "AGENT.md").get("mcp_servers", {})
                for server, declaration in self.base_manifest["mcp_servers"].items():
                    self.assertIn(server, servers)
                    self.assertEqual(_server_command(servers[server]), _server_command(declaration))

    def test_a2ui_catalogs(self) -> None:
        base = _catalog_ids(self.base_manifest["a2ui_catalogs"])
        for name in SUPERSET_PACKS:
            with self.subTest(pack=name):
                manifest = parse_frontmatter(REPO / name / "AGENT.md")
                self.assertLessEqual(set(base), set(_catalog_ids(manifest["a2ui_catalogs"])))

    def test_skills(self) -> None:
        required = DEFAULT_AGENT_BUILTIN_SKILLS | set(self.base_expert.get("skills", []))
        for name in SUPERSET_PACKS:
            with self.subTest(pack=name):
                self.assertLessEqual(required, set(_root_expert(REPO / name)["skills"]))

    def test_shipped_copies_of_base_skills_are_identical(self) -> None:
        for skill in self.base_expert.get("skills", []):
            source = (BASE / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            for name in SUPERSET_PACKS:
                with self.subTest(pack=name, skill=skill):
                    copy = REPO / name / "skills" / skill / "SKILL.md"
                    self.assertEqual(copy.read_text(encoding="utf-8"), source)

    def test_working_principles(self) -> None:
        base = _principles(_root_prompt(BASE))
        for requirement in (
            "create-dashboard",
            "review-visual-presentation",
            "one initial view",
            "recheck matching pixels",
            "rendered review is unavailable",
        ):
            self.assertIn(requirement, base)
        for name in SUPERSET_PACKS:
            with self.subTest(pack=name):
                self.assertEqual(_principles(_root_prompt(REPO / name)), base)

    def test_no_pack_copy_of_a_clio_builtin_skill(self) -> None:
        """A built-in is declared, never copied: a copy would drift from clio's."""

        for name in SUPERSET_PACKS:
            with self.subTest(pack=name):
                for skill in DEFAULT_AGENT_BUILTIN_SKILLS:
                    self.assertFalse((REPO / name / "skills" / skill).exists(), skill)


if __name__ == "__main__":
    unittest.main()
