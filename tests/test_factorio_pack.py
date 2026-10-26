"""Structural contract tests for the parent Factorio pack.

The same runtime contract ``test_factorio_flat_pack`` locks for Factorio Flat,
asserted on the parsed declarations of the parent pack: delegators are derived
from the consumed ``parent:`` edges, both of them select the adaptive briefing,
and every expert opts out of ``workflow_state`` and declares nothing the runtime
deleted or never reads. Prompt wording is left to the model and the evals.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

from tests.test_base_agent_policy import parse_frontmatter

ROOT = Path(__file__).resolve().parents[1] / "factorio"

# The runtime injects ``workflow_state`` unless an expert declares it false;
# ``evidence`` / ``errors`` / ``delegation`` are structured outputs it deleted and
# ``role`` is a key it never reads.
_LIVE_STRUCTURED_OUTPUTS = frozenset({"workflow_state"})
_DEAD_STRUCTURED_OUTPUTS = frozenset({"evidence", "errors", "delegation", "artifacts"})
_DEAD_EXPERT_KEYS = frozenset({"role"})


def _load_experts() -> dict[str, dict[str, Any]]:
    """Return every expert declared by the manifest, keyed by its declared id."""

    manifest = parse_frontmatter(ROOT / "AGENT.md")
    experts = (parse_frontmatter(ROOT / relative) for relative in manifest["experts"])
    return {parsed["id"]: parsed for parsed in experts}


class FactorioManifestTests(unittest.TestCase):
    """The manifest must point at exactly the expert files on disk."""

    def test_manifest_lists_exactly_the_expert_files_on_disk(self) -> None:
        manifest = parse_frontmatter(ROOT / "AGENT.md")
        declared = {str(relative) for relative in manifest["experts"]}
        on_disk = {path.relative_to(ROOT).as_posix() for path in (ROOT / "experts").glob("*.md")}

        self.assertEqual(declared, on_disk)
        self.assertEqual(manifest["root_expert"], "main")


class FactorioDelegationTests(unittest.TestCase):
    """Delegation is whatever the consumed ``parent:`` edges say it is."""

    def setUp(self) -> None:
        self.experts = _load_experts()
        self.parents = {
            expert_id: str(parsed.get("parent") or "") for expert_id, parsed in self.experts.items()
        }
        self.delegators = {parent for parent in self.parents.values() if parent}

    def test_parent_edges_resolve_and_agree_with_declared_children(self) -> None:
        derived: dict[str, set[str]] = {}
        for expert_id, parent in self.parents.items():
            if parent:
                self.assertIn(parent, self.experts, f"{expert_id} has a dangling parent")
                derived.setdefault(parent, set()).add(expert_id)

        self.assertEqual(self.delegators, {"main", "evidence_researcher"})
        for expert_id, parsed in self.experts.items():
            self.assertEqual(set(parsed.get("children") or []), derived.get(expert_id, set()))

    def test_delegators_opt_into_adaptive_delegation(self) -> None:
        """Without it a delegator gets the legacy 'route work, do not do it yourself' briefing.

        The root is a scientist-facing partner that answers directly when it can,
        and the evidence researcher's own prompt drives its fan-out.
        """

        for expert_id in self.delegators:
            self.assertEqual(
                str(self.experts[expert_id].get("delegation_policy") or "").lower(),
                "adaptive",
                f"{expert_id} would receive the legacy orchestrator briefing",
            )

    def test_the_root_declares_the_question_tool_its_prompt_uses(self) -> None:
        """``ask_user`` is attached only when declared, and the root owns every question."""

        self.assertIn("ask_user", self.experts["main"].get("tools") or [])
        self.assertIn("`ask_user`", (ROOT / "experts" / "main.md").read_text(encoding="utf-8"))


class FactorioExpertContractTests(unittest.TestCase):
    """Each expert declares an explicit structured-output posture and no inert keys."""

    def setUp(self) -> None:
        self.experts = _load_experts()

    def test_every_expert_opts_out_of_workflow_state_chrome(self) -> None:
        for expert_id, parsed in self.experts.items():
            structured_outputs = parsed["structured_outputs"]
            self.assertIsInstance(structured_outputs, dict, expert_id)
            self.assertIs(structured_outputs.get("workflow_state"), False, expert_id)

    def test_experts_declare_no_structured_output_the_runtime_deleted(self) -> None:
        for expert_id, parsed in self.experts.items():
            declared = set(parsed["structured_outputs"])
            self.assertEqual(declared & _DEAD_STRUCTURED_OUTPUTS, set(), expert_id)
            self.assertLessEqual(declared, _LIVE_STRUCTURED_OUTPUTS, expert_id)

    def test_experts_declare_no_key_the_runtime_never_reads(self) -> None:
        for expert_id, parsed in self.experts.items():
            self.assertEqual(set(parsed) & _DEAD_EXPERT_KEYS, set(), expert_id)


if __name__ == "__main__":
    unittest.main()
