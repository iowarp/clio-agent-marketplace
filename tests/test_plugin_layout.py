"""Dependency-free layout policy for the native plugin marketplace.

``clio-agent plugin check .`` is the authoritative validator (it loads every
plugin and resolves every agent exactly as install does). These checks run
without clio-agent so a plain interpreter catches layout drift early: plugin
manifests, skill folder names, fragment ids, agent classes, and that no
retired Agent Blueprint file comes back.
"""

from __future__ import annotations

import ast
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"
SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
MANIFEST_FIELDS = {
    "$schema",
    "name",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
    "extensions",
}
EXTENSION_FIELDS = {"kind", "requires", "members", "model", "prefers", "workflow_state", "catalogs"}
SKILL_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9]|-(?=[a-z0-9]))*$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _frontmatter(path: Path) -> dict[str, str]:
    """Top-level ``key: value`` pairs of a Markdown file's frontmatter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    head = text.split("---", 2)[1]
    return dict(
        (key.strip(), value.strip())
        for key, value in (line.split(":", 1) for line in head.splitlines() if ":" in line)
        if not key.startswith((" ", "\t", "-"))
    )


def _plugins() -> list[Path]:
    return sorted(path.parent for path in PLUGINS.glob("*/plugin.json"))


class PluginManifestTests(unittest.TestCase):
    def test_every_plugin_manifest_is_agent_plugins_1_0_0(self) -> None:
        for plugin in _plugins():
            with self.subTest(plugin=plugin.name):
                data = json.loads((plugin / "plugin.json").read_text(encoding="utf-8"))
                self.assertEqual(data["$schema"], SCHEMA)
                self.assertEqual(data["name"], plugin.name)
                self.assertRegex(data["version"], SEMVER)
                self.assertTrue(data["description"].strip())
                self.assertLessEqual(set(data), MANIFEST_FIELDS)
                ext = (data.get("extensions") or {}).get("ai.iowarp.clio") or {}
                self.assertLessEqual(set(ext), EXTENSION_FIELDS)
                if ext.get("kind") == "pack":
                    self.assertTrue(ext.get("members"))
                    self.assertFalse((plugin / "skills").exists())
                    self.assertFalse((plugin / "mcp.json").exists())

    def test_requirements_and_members_name_shipped_plugins(self) -> None:
        shipped = {plugin.name for plugin in _plugins()} | {"core", "orchestration"}
        for plugin in _plugins():
            data = json.loads((plugin / "plugin.json").read_text(encoding="utf-8"))
            ext = (data.get("extensions") or {}).get("ai.iowarp.clio") or {}
            for ref in [*ext.get("requires", []), *ext.get("members", [])]:
                with self.subTest(plugin=plugin.name, ref=ref):
                    self.assertIn(ref.split("@", 1)[0], shipped)

    def test_mcp_configs_are_stdio_or_remote_and_never_blueprint_relative(self) -> None:
        for path in sorted(PLUGINS.glob("*/mcp.json")):
            with self.subTest(plugin=path.parent.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(set(data), {"$schema", "mcpServers"})
                self.assertEqual(data["$schema"], MCP_SCHEMA)
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("CLIO_BLUEPRINT_DIR", text)
                self.assertNotIn("agent-blueprints", text)
                for name, server in data["mcpServers"].items():
                    self.assertRegex(name, r"^[A-Za-z0-9][A-Za-z0-9-]*$")
                    self.assertIn(server["type"], ("stdio", "streamable-http", "sse"))


class SkillAndFragmentTests(unittest.TestCase):
    def test_skill_names_match_their_hyphenated_folders(self) -> None:
        seen: dict[str, str] = {}
        for skill in sorted(PLUGINS.glob("*/skills/*/SKILL.md")):
            name = skill.parent.name
            with self.subTest(skill=f"{skill.parents[2].name}/{name}"):
                self.assertRegex(name, SKILL_NAME)
                self.assertEqual(_frontmatter(skill).get("name"), name)
                self.assertTrue(_frontmatter(skill).get("description"))
                self.assertNotIn(name, seen, f"also shipped by {seen.get(name)}")
                seen[name] = skill.parents[2].name

    def test_fragments_carry_their_plugin_id_and_a_known_section(self) -> None:
        for fragment in sorted(PLUGINS.glob("*/ai.iowarp.clio/prompt/**/*.md")):
            meta = _frontmatter(fragment)
            if "section" not in meta:
                continue
            plugin = fragment.relative_to(PLUGINS).parts[0]
            with self.subTest(fragment=fragment.relative_to(PLUGINS).as_posix()):
                self.assertTrue(meta["id"].startswith(f"{plugin}."))
                self.assertIn(meta["section"], ("capabilities", "domain"))

    def test_subagent_prompt_files_exist(self) -> None:
        for module in sorted(PLUGINS.glob("*/ai.iowarp.clio/subagents/*.py")):
            clio = module.parents[1]
            for match in re.findall(r'PromptFile\("([^"]+)"\)', module.read_text("utf-8")):
                with self.subTest(subagent=module.relative_to(PLUGINS).as_posix()):
                    self.assertTrue((clio / match).is_file())


class AgentClassTests(unittest.TestCase):
    def _classes(self) -> list[tuple[Path, ast.ClassDef]]:
        out = []
        for path in sorted((ROOT / "agents").glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            out.extend((path, node) for node in tree.body if isinstance(node, ast.ClassDef))
        return out

    def test_every_agent_has_a_unique_id_and_inherits_core(self) -> None:
        ids: set[str] = set()
        for path, node in self._classes():
            fields = {
                target.id: stmt.value
                for stmt in node.body
                if isinstance(stmt, ast.Assign)
                for target in stmt.targets
                if isinstance(target, ast.Name)
            }
            with self.subTest(agent=f"{path.name}:{node.name}"):
                agent_id = ast.literal_eval(fields["id"])
                self.assertNotIn(agent_id, ids)
                ids.add(agent_id)
                if "version" in fields:
                    self.assertRegex(ast.literal_eval(fields["version"]), SEMVER)
                self.assertTrue(ast.literal_eval(fields["role"]))
                plugins = fields.get("plugins")
                if plugins is None:  # inherits its parent's list unchanged
                    continue
                # Agent.plugins + [...] keeps "core"; a literal list must name it.
                if isinstance(plugins, ast.BinOp):
                    self.assertIsInstance(plugins.left, ast.Attribute)
                    self.assertEqual(plugins.left.attr, "plugins")
                else:
                    self.assertIn("core", ast.literal_eval(plugins))

    def test_no_agent_blueprint_files_remain(self) -> None:
        leftovers = [
            path.relative_to(ROOT).as_posix()
            for pattern in ("**/AGENT.md", "**/clio-pack.yaml", "*/experts/*.md")
            for path in ROOT.glob(pattern)
            if ".git" not in path.parts
        ]
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
