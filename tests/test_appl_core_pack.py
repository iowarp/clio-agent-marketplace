"""Structural and level-contract policy tests for the APPL-CORE Analyst pack.

Dependency-free (runs under CI's bare ``model-inheritance`` interpreter). The
pack's functional tests -- its scripts, eval tooling, and the real clio-agent
blueprint validator -- live in ``appl-core/tests`` and run in their own job.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import Any

from tests.test_base_agent_policy import parse_frontmatter

ROOT = Path(__file__).resolve().parents[1] / "appl-core"

#: Each skill's level. L3 (one experiment) never ships in the pack.
EXPECTED_LEVELS: dict[str, str] = {
    "onboard-dataset": "L0",
    "audit-dataset": "L0",
    "evidence-and-claims": "L0",
    "geometry-to-glb": "L0",
    "create-pdf-report": "L0",
    "phenotyping-onboarding-checks": "L1",
    "size-and-growth-traits": "L1",
    "treatment-response": "L1",
    "physiology-signals": "L1",
    "phenotyping-report": "L1",
    "appl-core-exports": "L2",
    "appl-instruments": "L2",
}
#: clio-agent builtin skills the expert may declare without shipping them.
BUILTIN_SKILLS = frozenset(
    {"present-interactive-analysis", "work-with-pdfs", "planning", "update-models"}
)
#: The built-in skills clio auto-declares on the default agent (Base Agent);
#: a non-default pack only gets them by declaring them.
DEFAULT_AGENT_BUILTIN_SKILLS = frozenset({"work-with-pdfs", "planning", "update-models"})
#: A root expert with a declared catalog gets all four A2UI producer tools.
A2UI_PRODUCER_TOOLS = frozenset(
    {
        "create_a2ui_surface",
        "update_a2ui_components",
        "update_a2ui_data_model",
        "delete_a2ui_surface",
    }
)
#: Tools clio-agent attaches automatically. Declaring them in ``tools`` is an
#: "unknown tool reference" validation error (they are not in TOOL_CATALOG).
AUTO_ATTACHED = frozenset(
    {
        "load_skill",
        "spawn_skill_task",
        "wait_agent_tasks",
        "spawn_agent_task",
        "create_artifact",
    }
)
#: Builtin tool names an expert may declare.
BUILTIN_TOOLS = frozenset(
    {
        "shell_bash",
        "fs_read_file",
        "fs_propose_edit",
        "fs_apply_edit_write",
        "view_image",
        "view_pdf",
        "ask_user",
        "create_a2ui_surface",
        "update_a2ui_components",
        "update_a2ui_data_model",
        "delete_a2ui_surface",
    }
)
L3_LITERALS = ("Weston", "2026.04.09", "OPAL.0002", "28773", "29014", "5577", "Thalpsi")


def _skill_dirs() -> list[Path]:
    return sorted(path.parent for path in (ROOT / "skills").glob("*/SKILL.md"))


def _shipped_text_files() -> list[Path]:
    """Every file the level contract covers: AGENT.md, experts, and all skill files."""

    files = [ROOT / "AGENT.md", *sorted((ROOT / "experts").glob("*.md"))]
    files.extend(
        p
        for p in sorted((ROOT / "skills").rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    )
    return files


class ApplCoreManifestTests(unittest.TestCase):
    """AGENT.md is loadable data with the declared runtime surface."""

    def setUp(self) -> None:
        self.manifest: dict[str, Any] = parse_frontmatter(ROOT / "AGENT.md")

    def test_identity_and_root(self) -> None:
        self.assertEqual(self.manifest["id"], "appl-core")
        self.assertEqual(self.manifest["title"], "APPL-CORE Analyst")
        self.assertEqual(self.manifest["display_name"], "APPL-CORE Analyst")
        self.assertEqual(self.manifest["root_expert"], "main")
        self.assertEqual(self.manifest["blueprint"], {"format": "agent-blueprint-v1"})
        self.assertEqual(self.manifest["defaults"], {"prompt_profile": "heavy"})
        self.assertEqual(self.manifest["experts"], ["experts/main.md"])
        self.assertIn("APPL-CORE", self.manifest["description"])

    def test_builtin_catalog_only_and_a_floor(self) -> None:
        self.assertEqual(self.manifest["a2ui_catalogs"], ["clio-workspace"])
        self.assertEqual(self.manifest["requires"], {"clio_agent": ">=0.9.4.23"})

    def test_clio_kit_servers_are_declared_like_the_other_packs(self) -> None:
        servers = self.manifest["mcp_servers"]
        self.assertEqual(sorted(servers), ["pandas", "parquet", "plot", "web"])
        for name, server in servers.items():
            with self.subTest(server=name):
                self.assertEqual(server["command"], "clio-kit")
                self.assertEqual(server["args"], ["mcp-server", name])


class ApplCoreExpertTests(unittest.TestCase):
    """The single react expert declares real tools and every shipped skill."""

    def setUp(self) -> None:
        self.expert: dict[str, Any] = parse_frontmatter(ROOT / "experts" / "main.md")
        self.namespaces = set(parse_frontmatter(ROOT / "AGENT.md")["mcp_servers"])

    def test_react_root(self) -> None:
        self.assertEqual(self.expert["id"], "main")
        self.assertEqual(self.expert["tier"], 1)
        self.assertEqual(self.expert["module"], {"kind": "react"})
        self.assertEqual(self.expert["a2ui_catalogs"], ["clio-workspace"])

    def test_tools_are_builtin_or_declared_mcp(self) -> None:
        tools = self.expert["tools"]
        self.assertEqual(len(tools), len(set(tools)))
        self.assertTrue({"shell_bash", "fs_read_file", "ask_user"} <= set(tools))
        for tool in tools:
            with self.subTest(tool=tool):
                self.assertNotIn(tool, AUTO_ATTACHED)
                self.assertTrue(
                    tool in BUILTIN_TOOLS or tool.split("_", 1)[0] in self.namespaces,
                    tool,
                )

    def test_tools_include_the_general_purpose_toolset(self) -> None:
        """The pack grants base-agent's normal capabilities; clio's permission
        system, not the tool list, decides what is actually allowed."""

        self.assertLessEqual(
            {
                "shell_bash",
                "fs_read_file",
                "fs_propose_edit",
                "fs_apply_edit_write",
                "view_image",
                "view_pdf",
                "web_fetch",
                "ask_user",
            },
            set(self.expert["tools"]),
        )

    def test_every_declared_skill_exists_and_every_skill_is_declared(self) -> None:
        declared = self.expert["skills"]
        shipped = {path.name for path in _skill_dirs()}
        self.assertEqual(len(declared), len(set(declared)))
        for skill in declared:
            with self.subTest(skill=skill):
                self.assertTrue(skill in shipped or skill in BUILTIN_SKILLS, skill)
        self.assertEqual(shipped - set(declared), set())
        self.assertLess(
            declared.index("onboard-dataset"), declared.index("audit-dataset")
        )

    def test_declares_the_builtin_skills_the_default_agent_gets(self) -> None:
        self.assertLessEqual(DEFAULT_AGENT_BUILTIN_SKILLS, set(self.expert["skills"]))

    def test_a2ui_tools_come_from_the_catalog_like_base_agent(self) -> None:
        self.assertEqual(set(self.expert["tools"]) & A2UI_PRODUCER_TOOLS, set())
        self.assertEqual(self.expert["a2ui_catalogs"], ["clio-workspace"])

    def test_prompt_carries_base_agent_working_principles(self) -> None:
        prompt = " ".join(
            (ROOT / "experts" / "main.md").read_text(encoding="utf-8").split()
        )
        self.assertIn("Never infer a file's contents from its name", prompt)
        self.assertIn("never claim the task succeeded", prompt)
        self.assertIn("load `work-with-pdfs`", prompt)
        self.assertIn("`create-pdf-report`; otherwise reports are Markdown", prompt)

    def test_prompt_states_the_card_first_contract(self) -> None:
        prompt = " ".join(
            (ROOT / "experts" / "main.md").read_text(encoding="utf-8").split()
        )
        self.assertIn(
            "<workspace_state>/datasets/<key>/experiment-card.md", prompt
        )
        self.assertIn("CLIO_AGENT_WORKSPACE_STATE_DIR", prompt)
        self.assertNotIn("--store <workspace_root>", prompt)
        self.assertIn("It is a convention, not a limit", prompt)
        self.assertIn("if an action is denied, report that plainly", prompt)
        self.assertNotIn("<bundle_root>/.clio", prompt)
        self.assertIn(
            "do not trust the returned card until you have re-run the returned loader yourself",
            prompt,
        )
        self.assertIn("ask the user (`ask_user`)", prompt)
        self.assertIn("`[stated]`, `[checked]`, or `[inferred]`", prompt)
        self.assertIn("check `export_version` first", prompt)

    def test_pack_does_not_impose_access_limits(self) -> None:
        """Permissions belong to clio (approval modes, deny rules, allowed roots,
        sandbox); the pack's docs must not declare the session or export
        read-only or forbid writes."""

        banned = re.compile(
            r"read-only input|never write|must not be written|"
            r"session is read-only|session as read-only",
            re.IGNORECASE,
        )
        for relative in (
            "AGENT.md",
            "experts/main.md",
            "skills/onboard-dataset/SKILL.md",
            "skills/audit-dataset/SKILL.md",
            "skills/phenotyping-onboarding-checks/SKILL.md",
        ):
            with self.subTest(doc=relative):
                text = " ".join((ROOT / relative).read_text(encoding="utf-8").split())
                self.assertIsNone(banned.search(text))

    def test_docs_default_artefacts_to_the_workspace_store(self) -> None:
        """By default per-dataset artefacts live in the workspace store."""

        bundle_local = re.compile(
            r"(<bundle_root>|BUNDLE_ROOT)[/\\]\.clio", re.IGNORECASE
        )
        for path in sorted(ROOT.rglob("*")):
            if path.suffix not in {".md", ".py", ".json"} or "tests" in path.parts:
                continue
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                text = path.read_text(encoding="utf-8")
                self.assertIsNone(bundle_local.search(text))
        for relative in (
            "AGENT.md",
            "experts/main.md",
            "skills/onboard-dataset/SKILL.md",
            "skills/audit-dataset/SKILL.md",
            "skills/phenotyping-onboarding-checks/SKILL.md",
        ):
            with self.subTest(doc=relative):
                text = " ".join((ROOT / relative).read_text(encoding="utf-8").split())
                self.assertIn("<workspace_state>/datasets/<key>/", text)
                self.assertNotIn(".clio/datasets/<key>/", text)


class ApplCoreSkillTests(unittest.TestCase):
    """Skill frontmatter stays inside what clio-agent's skill parser reads."""

    def test_every_skill_has_a_level_and_the_expected_one(self) -> None:
        self.assertEqual({path.name for path in _skill_dirs()}, set(EXPECTED_LEVELS))
        for skill_dir in _skill_dirs():
            with self.subTest(skill=skill_dir.name):
                meta = parse_frontmatter(skill_dir / "SKILL.md")
                self.assertEqual(meta["name"], skill_dir.name)
                self.assertTrue(str(meta["title"]).strip())
                self.assertTrue(str(meta["description"]).strip())
                self.assertLessEqual(
                    set(meta), {"name", "title", "description", "keywords", "effect"}
                )
                levels = [k for k in meta["keywords"] if str(k).startswith("level:")]
                self.assertEqual(levels, [f"level:{EXPECTED_LEVELS[skill_dir.name]}"])

    def test_keyword_items_use_the_form_clio_agent_parses(self) -> None:
        """clio-agent's skill frontmatter parser only reads list items that start at
        column 0 with ``- ``; an indented ``  - level:L0`` would parse as a key."""

        for skill_dir in _skill_dirs():
            with self.subTest(skill=skill_dir.name):
                head = (
                    (skill_dir / "SKILL.md")
                    .read_text(encoding="utf-8")
                    .split("---", 2)[1]
                )
                self.assertIsNone(re.search(r"^[ \t]+-[ \t]", head, re.MULTILINE))
                self.assertRegex(head, r"(?m)^- level:L[0-2]$")

    def test_only_the_audit_skill_spawns_a_child(self) -> None:
        for skill_dir in _skill_dirs():
            with self.subTest(skill=skill_dir.name):
                effect = parse_frontmatter(skill_dir / "SKILL.md").get("effect")
                expected = (
                    "spawn_subagent_with_skill"
                    if skill_dir.name == "audit-dataset"
                    else None
                )
                self.assertEqual(effect, expected)
        audit = " ".join(
            (ROOT / "skills" / "audit-dataset" / "SKILL.md")
            .read_text(encoding="utf-8")
            .split()
        )
        self.assertIn(
            "You are already running this skill in the delegated child", audit
        )
        self.assertIn("re-runs the loader and compares the view hashes", audit)

    def test_script_skills_ship_their_scripts(self) -> None:
        for relative in (
            "onboard-dataset/scripts/inventory.py",
            "onboard-dataset/scripts/audit_columns.py",
            "onboard-dataset/scripts/join_keys.py",
            "onboard-dataset/scripts/flag_check.py",
            "onboard-dataset/scripts/card.py",
            "geometry-to-glb/scripts/to_glb.py",
            "phenotyping-onboarding-checks/scripts/validate_views.py",
        ):
            with self.subTest(script=relative):
                path = ROOT / "skills" / relative
                self.assertTrue(path.is_file())
                self.assertTrue(
                    path.read_text(encoding="utf-8").startswith("# /// script\n")
                )
                skill = (path.parents[1] / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn(f'"SKILL_ROOT/scripts/{path.name}"', skill)
        for kind in ("design", "observations", "spectra", "assets", "events"):
            self.assertTrue(
                (
                    ROOT
                    / "skills"
                    / "phenotyping-onboarding-checks"
                    / "schemas"
                    / f"{kind}.schema.json"
                ).is_file()
            )


class ApplCoreLevelContractTests(unittest.TestCase):
    """No experiment-level (L3) literal ships in the pack."""

    def test_lint_marker_and_denylist_are_present(self) -> None:
        self.assertTrue((ROOT / ".lint-l3").is_file())
        literals = [
            line.strip()
            for line in (ROOT / "lint-denylist.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        self.assertEqual(sorted(literals), sorted(L3_LITERALS))

    def test_no_denylisted_literal_in_shipped_files(self) -> None:
        for path in _shipped_text_files():
            text = path.read_text(encoding="utf-8", errors="replace").casefold()
            for literal in L3_LITERALS:
                with self.subTest(
                    path=path.relative_to(ROOT).as_posix(), literal=literal
                ):
                    self.assertNotIn(literal.casefold(), text)


if __name__ == "__main__":
    unittest.main()
