"""Structural contract tests for the Factorio Flat pack.

These assert the *parsed* blueprint declaration, never the wording of its prose.
A pack is data the runtime loads, so the only policy worth locking is what the
runtime actually consumes: the ``parent:`` edge set (which is what makes an
expert a delegator — ``children:`` is not read by the loader), the declared tool
surface, and an explicit structured-output posture. Prompt wording belongs to
the model and to the behavioral evals, not to a substring grep.

The strict frontmatter parser is shared with the Base Agent policy tests: it
RAISES on any shape it does not understand, so a malformed declaration fails
loudly instead of yielding a partial mapping that makes an assertion vacuous.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import Any

from tests.test_base_agent_policy import parse_frontmatter


ROOT = Path(__file__).resolve().parents[1] / "factorio-flat"

_TOOL_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_MARKDOWN_LINK = re.compile(r"\]\((?P<target>[^)#:]+\.md)\)")

# The runtime's live structured-output contract: ``workflow_state`` is the ONE
# injected structured field, and an expert that does not declare it gets it
# injected by default (``structured.get(name, True)`` in the runtime's signature
# builder). Silence therefore means "yes"; opting out has to be explicit.
_LIVE_STRUCTURED_OUTPUTS = frozenset({"workflow_state"})

# Frontmatter keys no runtime consumer reads. ``role`` is never looked up;
# ``evidence`` / ``errors`` / ``delegation`` were structured outputs the runtime
# deleted. Declaring them only invites the reader to believe they do something.
_DEAD_EXPERT_KEYS = frozenset({"role"})
_DEAD_STRUCTURED_OUTPUTS = frozenset({"evidence", "errors", "delegation", "artifacts"})


def _load_experts() -> dict[str, dict[str, Any]]:
    """Return every expert declared by the manifest, keyed by its declared id."""

    manifest = parse_frontmatter(ROOT / "AGENT.md")
    experts: dict[str, dict[str, Any]] = {}
    for relative in manifest["experts"]:
        parsed = parse_frontmatter(ROOT / relative)
        experts[parsed["id"]] = parsed
    return experts


class FactorioFlatManifestTests(unittest.TestCase):
    """The manifest must be loadable data pointing at real expert files."""

    def setUp(self) -> None:
        self.manifest = parse_frontmatter(ROOT / "AGENT.md")

    def test_manifest_declares_a_distinct_workflow_free_pack(self) -> None:
        """The flat id is additive and declares no deterministic workflow."""

        self.assertEqual(self.manifest["id"], "factorio-flat")
        self.assertEqual(self.manifest["blueprint"], {"format": "agent-blueprint-v1"})
        self.assertNotIn("workflow", self.manifest)
        self.assertTrue((ROOT.parent / "factorio" / "AGENT.md").is_file())

    def test_manifest_lists_exactly_the_expert_files_on_disk(self) -> None:
        """An unlisted expert file is invisible to the runtime, so forbid drift."""

        declared = {str(relative) for relative in self.manifest["experts"]}
        on_disk = {
            path.relative_to(ROOT).as_posix() for path in (ROOT / "experts").glob("*.md")
        }

        self.assertEqual(declared, on_disk)

    def test_root_expert_resolves_to_a_declared_expert(self) -> None:
        """``root_expert`` names an expert this manifest actually ships."""

        experts = _load_experts()

        self.assertIn(self.manifest["root_expert"], experts)
        self.assertEqual(self.manifest["root_expert"], "main")

    def test_manifest_records_clio_kit_provisioning(self) -> None:
        """Sibling parity: the manifest carries the provisioning rationale.

        The comment is the only place a deployer learns that the declared web
        MCP resolves through an installed clio-kit launcher rather than ``uvx``.
        """

        frontmatter = (ROOT / "AGENT.md").read_text(encoding="utf-8").split("---")[1]

        self.assertIn("uv tool install clio-kit", frontmatter)
        self.assertIn("uv cache", frontmatter)


class FactorioFlatDelegationEdgeTests(unittest.TestCase):
    """Delegation is whatever the CONSUMED ``parent:`` edges say it is."""

    def setUp(self) -> None:
        self.experts = _load_experts()
        self.parents = {
            expert_id: str(parsed.get("parent") or parsed.get("parent_id") or "")
            for expert_id, parsed in self.experts.items()
        }

    def _delegators(self) -> set[str]:
        """Return every expert another expert declares as its parent."""

        return {parent for parent in self.parents.values() if parent}

    def test_every_declared_parent_resolves_to_a_shipped_expert(self) -> None:
        """A dangling parent edge is a load-time pack validation error."""

        for expert_id, parent in self.parents.items():
            if parent:
                self.assertIn(parent, self.experts, f"{expert_id} has a dangling parent")

    def test_exactly_the_root_and_evidence_coordinator_hold_children(self) -> None:
        """Only two experts sit on the receiving end of a ``parent:`` edge.

        This is the invariant a re-parented expert must break: adding a third
        delegator changes the derived set, whatever the prose or any
        unconsumed ``children:`` block happens to say.
        """

        self.assertEqual(self._delegators(), {"main", "evidence_researcher"})

    def test_only_the_root_expert_declares_no_parent(self) -> None:
        """Every non-root expert is reachable through exactly one parent edge."""

        rootless = {expert for expert, parent in self.parents.items() if not parent}

        self.assertEqual(rootless, {"main"})

    def test_declared_children_agree_with_the_derived_parent_edges(self) -> None:
        """``children:`` is documentation; it must not contradict the loader.

        The runtime derives the edge set from ``parent:`` alone, so a
        ``children:`` block that disagrees describes a pack that does not exist.
        """

        derived: dict[str, set[str]] = {}
        for expert_id, parent in self.parents.items():
            if parent:
                derived.setdefault(parent, set()).add(expert_id)

        for expert_id, parsed in self.experts.items():
            declared = parsed.get("children")
            if declared is None:
                self.assertNotIn(expert_id, derived, f"{expert_id} owns undeclared children")
                continue
            self.assertIsInstance(declared, list)
            self.assertEqual(set(declared), derived.get(expert_id, set()))

    def test_delegators_declare_a_react_module(self) -> None:
        """The runtime refuses declared children on a non-react parent."""

        for expert_id in self._delegators():
            self.assertEqual(self.experts[expert_id]["module"], {"kind": "react"})

    def test_delegators_opt_into_adaptive_delegation(self) -> None:
        """Both delegators avoid the legacy 'you have NO tools of your own' briefing.

        The default child briefing tells an expert it owns no tools; both of
        this pack's delegators declare ``ask_user`` (and the root declares a
        surface tool), so both must select the adaptive briefing instead.
        """

        for expert_id in self._delegators():
            self.assertEqual(
                str(self.experts[expert_id].get("delegation_policy") or "").lower(),
                "adaptive",
                f"{expert_id} would receive the legacy orchestrator briefing",
            )


class FactorioFlatExpertContractTests(unittest.TestCase):
    """Each expert declares an explicit, least-privilege runtime contract."""

    def setUp(self) -> None:
        self.experts = _load_experts()

    def test_every_expert_declares_a_react_module_over_a_typed_signature(self) -> None:
        """Every expert is a react loop answering into a typed ``answer`` field."""

        for expert_id, parsed in self.experts.items():
            self.assertEqual(parsed["module"], {"kind": "react"}, expert_id)
            self.assertIn("question", parsed["signature"]["inputs"], expert_id)
            self.assertIn("answer", parsed["signature"]["outputs"], expert_id)

    def test_every_expert_opts_out_of_workflow_state_chrome(self) -> None:
        """The pack declares no workflow, so no expert should emit workflow state.

        Omission is not opt-out: the runtime injects ``workflow_state`` unless an
        expert says ``false``, so the posture is asserted as a parsed value on
        all nine experts.
        """

        for expert_id, parsed in self.experts.items():
            structured_outputs = parsed["structured_outputs"]
            self.assertIsInstance(structured_outputs, dict, expert_id)
            self.assertIs(structured_outputs.get("workflow_state"), False, expert_id)

    def test_experts_declare_no_structured_output_the_runtime_deleted(self) -> None:
        """Only the live structured field may appear in a declaration."""

        for expert_id, parsed in self.experts.items():
            declared = set(parsed["structured_outputs"])
            self.assertEqual(declared & _DEAD_STRUCTURED_OUTPUTS, set(), expert_id)
            self.assertLessEqual(declared, _LIVE_STRUCTURED_OUTPUTS, expert_id)

    def test_experts_declare_no_key_the_runtime_never_reads(self) -> None:
        """Inert frontmatter reads as policy it is not; keep it out."""

        for expert_id, parsed in self.experts.items():
            self.assertEqual(set(parsed) & _DEAD_EXPERT_KEYS, set(), expert_id)

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
        for expert_id, tools in expected.items():
            declared = self.experts[expert_id].get("tools") or []
            self.assertEqual(declared, tools, expert_id)
            for tool in declared:
                self.assertRegex(tool, _TOOL_NAME)

    def test_create_artifact_is_never_pinned_to_an_expert_allowlist(self) -> None:
        """Durable dossiers use the auto-attached artifact tool, not an allowlist."""

        dossier = (ROOT / "skills/maintain-scientific-dossier/SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("`create_artifact`", dossier)
        for expert_id, parsed in self.experts.items():
            self.assertNotIn("create_artifact", parsed.get("tools") or [], expert_id)


class FactorioFlatSkillWiringTests(unittest.TestCase):
    """Declared skills and their progressive-disclosure links must resolve."""

    def setUp(self) -> None:
        self.experts = _load_experts()

    def test_every_declared_skill_ships_in_the_pack(self) -> None:
        """A declared skill id the pack does not ship never loads at runtime."""

        declared: set[str] = set()
        for parsed in self.experts.values():
            declared.update(parsed.get("skills") or [])
        bundled = {path.parent.name for path in ROOT.glob("skills/*/SKILL.md")}

        self.assertTrue(declared)
        self.assertEqual(declared, bundled)

    def test_every_skill_declares_the_name_its_directory_claims(self) -> None:
        """``load_skill`` addresses a skill by id, so the two must agree."""

        for path in sorted(ROOT.glob("skills/*/SKILL.md")):
            self.assertEqual(parse_frontmatter(path)["name"], path.parent.name)

    def test_every_bundled_reference_link_resolves(self) -> None:
        """Progressive disclosure is only real when the linked file exists."""

        for path in sorted(ROOT.glob("skills/**/*.md")):
            text = path.read_text(encoding="utf-8")
            for match in _MARKDOWN_LINK.finditer(text):
                target = (path.parent / match.group("target")).resolve()
                self.assertTrue(target.is_file(), f"{path}: broken link {match.group('target')}")

    def test_design_note_uses_only_first_party_prompt_sources(self) -> None:
        """The compact rationale cites the three requested public source families."""

        note = (ROOT / "README.md").read_text(encoding="utf-8")
        urls = re.findall(r"https://[^)\s]+", note)
        allowed = ("developers.openai.com", "anthropic.com", "ai.google.dev")

        self.assertTrue(urls)
        for domain in allowed:
            self.assertTrue(any(domain in url for url in urls), domain)
        for url in urls:
            self.assertTrue(any(domain in url for domain in allowed), url)


if __name__ == "__main__":
    unittest.main()
