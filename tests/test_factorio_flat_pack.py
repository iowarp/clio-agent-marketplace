"""Static marketplace contracts for the Factorio Flat pack."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "factorio-flat"


def _read(relative_path: str) -> str:
    """Return one Factorio Flat source file as UTF-8 text."""

    return (ROOT / relative_path).read_text(encoding="utf-8")


def _frontmatter(relative_path: str) -> str:
    """Return the leading YAML frontmatter text."""

    text = _read(relative_path)
    match = re.match(r"\A---\s*\n(?P<meta>.*?)\n---\s*\n", text, re.DOTALL)
    if match is None:
        raise AssertionError(f"missing frontmatter: {relative_path}")
    return match.group("meta")


def _body(relative_path: str) -> str:
    """Return Markdown after frontmatter."""

    text = _read(relative_path)
    return re.split(r"\n---\s*\n", text, maxsplit=1)[1].strip()


def _top_level_list(relative_path: str, field: str) -> list[str]:
    """Return one top-level YAML list from simple expert frontmatter."""

    lines = _frontmatter(relative_path).splitlines()
    values: list[str] = []
    active = False
    for line in lines:
        if line and not line.startswith(" "):
            active = line == f"{field}:"
            continue
        if active and line.startswith("  - "):
            values.append(line[4:].strip())
        elif active and line.strip() and not line.startswith("  - "):
            break
    return values


class FactorioFlatPackTests(unittest.TestCase):
    """Lock the flat prompt, tool ownership, and progressive disclosure."""

    experts = (
        {
            path.stem: path.relative_to(ROOT).as_posix()
            for path in (ROOT / "experts").glob("*.md")
        }
        if (ROOT / "experts").exists()
        else {}
    )

    def test_manifest_declares_a_distinct_workflow_free_pack(self) -> None:
        """The new id is additive and retains an agent-driven research shape."""

        manifest = _frontmatter("AGENT.md")

        self.assertIn("id: factorio-flat", manifest)
        self.assertIn("root_expert: main", manifest)
        self.assertNotRegex(manifest, r"(?m)^workflow:")
        self.assertTrue((ROOT.parent / "factorio" / "AGENT.md").is_file())

    def test_root_prompt_is_concise_identity_and_integrity_only(self) -> None:
        """Lifecycle choreography stays out of the always-on root prompt."""

        body = _body("experts/main.md")
        lowered = body.lower()

        self.assertLessEqual(len(body.split()), 150)
        self.assertIn("scientist", lowered)
        self.assertIn("integrity", lowered)
        self.assertIn("skill", lowered)
        for forbidden in (
            "spawn_agent_task",
            "spawn_agents_parallel",
            "wait_agent_tasks",
            "parent-mediated",
            "greeting",
            "fixed workflow",
        ):
            self.assertNotIn(forbidden, lowered)

    def test_tools_are_explicitly_least_privilege(self) -> None:
        """Interactive, presentation, and web tools stay with their owners."""

        expected = {
            "main": ["ask_user", "create_a2ui_surface"],
            "research_methodologist": ["ask_user"],
            "virtual_lab": ["ask_user", "create_a2ui_surface"],
            "evidence_researcher": ["ask_user"],
            "evidence_leaf": ["web_search", "web_fetch"],
            "evidence_critic": ["web_search", "web_fetch"],
            "simulation_methodologist": ["ask_user", "create_a2ui_surface"],
            "abaqus_engineer": ["ask_user"],
            "independent_reviewer": [],
        }

        self.assertEqual(set(self.experts), set(expected))
        for expert, tools in expected.items():
            self.assertEqual(_top_level_list(self.experts[expert], "tools"), tools)

    def test_only_two_experts_can_delegate(self) -> None:
        """Delegation belongs only to the principal and evidence coordinator."""

        delegators = {
            expert
            for expert, path in self.experts.items()
            if re.search(r"(?m)^  delegation: true$", _frontmatter(path))
        }
        child_owners = {
            expert
            for expert, path in self.experts.items()
            if _top_level_list(path, "children")
        }

        self.assertEqual(delegators, {"main", "evidence_researcher"})
        self.assertEqual(child_owners, delegators)

    def test_coordination_and_evidence_skills_use_progressive_disclosure(self) -> None:
        """Detailed task mechanics live in bundled references loaded on demand."""

        coordinate = _body("skills/coordinate-scientific-work/SKILL.md")
        evidence = _body("skills/evidence-fanout/SKILL.md")

        self.assertLessEqual(len(coordinate.split()), 180)
        self.assertIn("references/decision-criteria.md", coordinate)
        self.assertIn("references/task-lifecycle.md", coordinate)
        self.assertLessEqual(len(evidence.split()), 180)
        self.assertIn("references/fanout-lifecycle.md", evidence)
        self.assertIn("references/source-integrity.md", evidence)
        for relative_path in (
            "skills/coordinate-scientific-work/references/decision-criteria.md",
            "skills/coordinate-scientific-work/references/task-lifecycle.md",
            "skills/evidence-fanout/references/fanout-lifecycle.md",
            "skills/evidence-fanout/references/source-integrity.md",
        ):
            self.assertTrue((ROOT / relative_path).is_file())

    def test_task_lifecycle_covers_identity_wait_resume_and_synthesis(self) -> None:
        """The disclosed lifecycle preserves durable child consultations."""

        lifecycle = _read(
            "skills/coordinate-scientific-work/references/task-lifecycle.md"
        )
        prose = " ".join(lifecycle.split()).lower()

        for required in (
            "task id",
            "wait_agent_tasks",
            "same task",
            "resume",
            "synthes",
        ):
            self.assertIn(required, prose)

    def test_create_artifact_remains_runtime_compatible(self) -> None:
        """Durable dossiers use the auto-attached artifact tool without allowlist pins."""

        dossier = _body("skills/maintain-scientific-dossier/SKILL.md")

        self.assertIn("`create_artifact`", dossier)
        for path in self.experts.values():
            self.assertNotIn("create_artifact", _top_level_list(path, "tools"))

    def test_design_note_uses_only_first_party_prompt_sources(self) -> None:
        """The compact rationale cites the three requested public source families."""

        note = _read("README.md")
        urls = re.findall(r"https://[^)\s]+", note)

        self.assertTrue(any("developers.openai.com" in url for url in urls))
        self.assertTrue(any("anthropic.com" in url for url in urls))
        self.assertTrue(any("ai.google.dev" in url for url in urls))
        self.assertTrue(
            all(
                any(
                    domain in url
                    for domain in (
                        "developers.openai.com",
                        "anthropic.com",
                        "ai.google.dev",
                    )
                )
                for url in urls
            )
        )


if __name__ == "__main__":
    unittest.main()
