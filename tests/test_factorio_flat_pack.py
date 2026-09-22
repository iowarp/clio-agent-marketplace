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

import importlib.util
import re
import tempfile
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

    return {parsed["id"]: parsed for parsed, _ in _load_expert_files().values()}


def _load_expert_files() -> dict[str, tuple[dict[str, Any], str]]:
    """Return ``id -> (parsed frontmatter, manifest-relative path)`` per expert."""

    manifest = parse_frontmatter(ROOT / "AGENT.md")
    loaded: dict[str, tuple[dict[str, Any], str]] = {}
    for relative in manifest["experts"]:
        parsed = parse_frontmatter(ROOT / relative)
        loaded[parsed["id"]] = (parsed, str(relative))
    return loaded


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
        on_disk = {path.relative_to(ROOT).as_posix() for path in (ROOT / "experts").glob("*.md")}

        self.assertEqual(declared, on_disk)

    def test_root_expert_resolves_to_a_declared_expert(self) -> None:
        """``root_expert`` names an expert this manifest actually ships."""

        experts = _load_experts()

        self.assertIn(self.manifest["root_expert"], experts)
        self.assertEqual(self.manifest["root_expert"], "main")

    def test_manifest_declares_the_web_mcp_its_leaves_depend_on(self) -> None:
        """``web_search`` / ``web_fetch`` come from this declared server, not thin air.

        Asserted before the comment below it: the comment explains how the
        server is provisioned, so guarding the prose while leaving the
        declaration free to be dropped or repointed would be backwards.
        """

        servers = self.manifest["mcp_servers"]

        self.assertIsInstance(servers, dict)
        self.assertEqual(servers["web"], "clio-kit mcp-server web")

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

    def test_tier_agrees_with_the_parent_edge(self) -> None:
        """A tier that disagrees with the edge set DISABLES the expert at load.

        The loader errors ``tier > 1 experts must declare parent_id`` and an
        expert carrying errors loads disabled — so a root at ``tier: 2`` bricks
        the pack silently.
        """

        for expert_id, parsed in self.experts.items():
            tier = parsed["tier"]
            self.assertIsInstance(tier, int, expert_id)
            if self.parents[expert_id]:
                self.assertGreater(tier, 1, f"{expert_id} has a parent but claims tier {tier}")
            else:
                self.assertEqual(tier, 1, f"{expert_id} is the root but claims tier {tier}")

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
        loaded = _load_expert_files()
        self.experts = {expert_id: parsed for expert_id, (parsed, _) in loaded.items()}
        self.expert_paths = {expert_id: path for expert_id, (_, path) in loaded.items()}

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

    def test_no_expert_pins_a_model_or_provider(self) -> None:
        """Every expert inherits the session's provider and model.

        The loader honours a bare ``model:`` / ``provider:`` as well as the
        ``default_model:`` the repo's pin checker scans for, so a pack-local
        assertion is what actually keeps this pack model-agnostic.

        Deliberately stricter than ``scripts/check_model_pins.py``, which allows
        a ``default_model:`` carrying an adjacent ``# model-pin-justification:``
        comment. This pack is an A/B evaluation surface: a pin here would make
        two variants incomparable, so it has no justified form. Relax this test
        first if that ever stops being true.
        """

        for expert_id, parsed in self.experts.items():
            for key in ("model", "default_model", "provider", "default_provider", "api_base"):
                self.assertNotIn(key, parsed, f"{expert_id} pins {key}")

    def test_every_expert_ships_a_prompt_body(self) -> None:
        """An expert with no body loads DISABLED ('must provide a prompt body')."""

        for expert_id, relative in self.expert_paths.items():
            body = re.split(r"(?m)^---\s*$", (ROOT / relative).read_text(encoding="utf-8"))[2]
            self.assertTrue(body.strip(), f"{expert_id} ships an empty prompt body")

    def test_tools_are_explicitly_least_privilege(self) -> None:
        """Interactive, presentation, and web tools stay with their owners."""

        expected = {
            "main": ["ask_user", "create_a2ui_surface", "view_image"],
            "research_methodologist": ["ask_user"],
            "virtual_lab": ["ask_user", "create_a2ui_surface"],
            "evidence_researcher": ["ask_user"],
            "evidence_leaf": ["web_search", "web_fetch"],
            "evidence_critic": ["web_search", "web_fetch"],
            "simulation_methodologist": ["ask_user", "create_a2ui_surface"],
            "abaqus_engineer": ["ask_user"],
            "independent_reviewer": [],
            "materials_scientist": ["ask_user"],
            "manufacturing_expert": ["ask_user"],
            "characterization_expert": ["ask_user"],
            "mechanical_testing_expert": ["ask_user"],
            "fatigue_failure_expert": ["ask_user"],
            "data_analysis_expert": ["ask_user"],
        }

        self.assertEqual(set(self.experts), set(expected))
        for expert_id, tools in expected.items():
            declared = self.experts[expert_id].get("tools") or []
            self.assertEqual(declared, tools, expert_id)
            for tool in declared:
                self.assertRegex(tool, _TOOL_NAME)

    def test_create_artifact_is_never_pinned_to_an_expert_allowlist(self) -> None:
        """Durable deliverables use the auto-attached artifact tool, not an allowlist.

        There is no dedicated dossier skill in the materials-science taxonomy;
        the guarantee lives in the pack-level README instead.
        """

        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("`create_artifact`", readme)
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

    def test_every_skill_declares_a_description(self) -> None:
        """The description is the always-visible half of progressive disclosure.

        It is what the model reads when deciding whether to load the skill at
        all, so a skill without one is a skill that is never chosen on purpose.
        """

        for path in sorted(ROOT.glob("skills/*/SKILL.md")):
            description = parse_frontmatter(path).get("description")
            self.assertIsInstance(description, str, path.parent.name)
            self.assertTrue(description.strip(), path.parent.name)

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


class FactorioFlatPdfSkillTests(unittest.TestCase):
    """The PDF skill must be wired and its preparation helper must be functional."""

    def setUp(self) -> None:
        script_path = ROOT / "skills" / "work-with-pdfs" / "scripts" / "prepare_pdf.py"
        spec = importlib.util.spec_from_file_location("factorio_flat_prepare_pdf", script_path)
        if spec is None or spec.loader is None:
            self.fail(f"cannot import {script_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.helper = module

    def test_root_expert_can_load_the_pdf_skill(self) -> None:
        """PDF work starts at the scientist-facing root and loads on demand."""

        main = parse_frontmatter(ROOT / "experts" / "main.md")

        self.assertIn("work-with-pdfs", main["skills"])

    def test_helper_records_real_outputs_from_both_stages(self) -> None:
        """A successful preparation records concrete text and page artifacts."""

        def converter(source: Path, markdown: Path, structured: Path, max_pages: int) -> None:
            self.assertEqual(max_pages, 5)
            markdown.write_text("# Converted\n", encoding="utf-8")
            structured.write_text("{}\n", encoding="utf-8")

        def renderer(source: Path, pages: Path, max_pages: int, dpi: int) -> list[Path]:
            self.assertEqual((max_pages, dpi), (5, 96))
            pages.mkdir(parents=True)
            rendered = [pages / "page-0001.png", pages / "page-0002.png"]
            for path in rendered:
                path.write_bytes(b"png")
            return rendered

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "paper.pdf"
            source.write_bytes(b"%PDF-1.7\n")
            result = self.helper.prepare_pdf(
                source,
                root / "prepared",
                max_pages=5,
                dpi=96,
                converter=converter,
                renderer=renderer,
            )

            manifest = Path(result["manifest"])
            recorded = __import__("json").loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "complete")
            self.assertEqual(recorded["docling"]["status"], "complete")
            self.assertEqual(recorded["pages"]["count"], 2)

    def test_helper_preserves_a_docling_failure_when_pages_render(self) -> None:
        """A fallback image set is useful without hiding the failed text conversion."""

        def converter(source: Path, markdown: Path, structured: Path, max_pages: int) -> None:
            raise RuntimeError("conversion unavailable")

        def renderer(source: Path, pages: Path, max_pages: int, dpi: int) -> list[Path]:
            pages.mkdir(parents=True)
            rendered = pages / "page-0001.png"
            rendered.write_bytes(b"png")
            return [rendered]

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "scan.pdf"
            source.write_bytes(b"%PDF-1.7\n")
            result = self.helper.prepare_pdf(
                source,
                root / "prepared",
                converter=converter,
                renderer=renderer,
            )

            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["docling"]["status"], "failed")
            self.assertEqual(result["pages"]["status"], "complete")

    def test_helper_rejects_non_pdf_inputs_before_running_stages(self) -> None:
        """The script must not send an arbitrary workspace file into PDF tooling."""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "notes.txt"
            source.write_text("not a pdf", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "existing .pdf"):
                self.helper.prepare_pdf(source, root / "prepared")


if __name__ == "__main__":
    unittest.main()
