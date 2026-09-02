"""Black-box semantic evals for Factorio Flat conversations and traces."""

from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.evaluate_factorio_flat import evaluate_case, evaluate_files


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "factorio-flat" / "evals" / "behavioral-cases.json"
RESULTS = ROOT / "tests" / "fixtures" / "factorio-flat-behavioral-results.json"


class FactorioFlatBlackBoxEvalTests(unittest.TestCase):
    """Evaluate only public responses and normalized runtime traces."""

    def test_reference_traces_pass_all_behavioral_cases(self) -> None:
        """The semantic contracts accept representative compliant behavior."""

        self.assertEqual(evaluate_files(CASES, RESULTS), [])

    def test_cases_cover_the_six_requested_behaviors(self) -> None:
        """The fixture corpus covers the intended external behavior boundary."""

        cases = json.loads(CASES.read_text(encoding="utf-8"))

        self.assertEqual(
            {case["id"] for case in cases},
            {
                "greeting",
                "simple_question",
                "useful_clarification",
                "focused_skill_and_delegation",
                "parallel_investigation",
                "blocked_child_resume",
            },
        )

    def test_eval_rejects_unnecessary_delegation_for_simple_question(self) -> None:
        """Direct scientific questions must not trigger coordinator overhead."""

        cases = json.loads(CASES.read_text(encoding="utf-8"))
        results = json.loads(RESULTS.read_text(encoding="utf-8"))
        case = next(item for item in cases if item["id"] == "simple_question")
        result = deepcopy(
            next(item for item in results if item["case_id"] == case["id"])
        )
        result["actions"].append(
            {
                "name": "spawn_agent_task",
                "arguments": {
                    "agent": "research_methodologist",
                    "task": "Define stress.",
                },
                "result": {"tasks": [{"task_id": "unnecessary", "status": "accepted"}]},
            }
        )

        failures = evaluate_case(case, result)

        self.assertTrue(
            any("forbidden action" in failure.message for failure in failures)
        )

    def test_eval_rejects_replacing_a_blocked_child(self) -> None:
        """A blocked consultation must resume with its original task identity."""

        cases = json.loads(CASES.read_text(encoding="utf-8"))
        results = json.loads(RESULTS.read_text(encoding="utf-8"))
        case = next(item for item in cases if item["id"] == "blocked_child_resume")
        result = deepcopy(
            next(item for item in results if item["case_id"] == case["id"])
        )
        result["actions"].insert(
            -1,
            {
                "name": "spawn_agent_task",
                "arguments": {
                    "agent": "simulation_methodologist",
                    "task": "Replace the paused consultation.",
                },
                "result": {
                    "tasks": [{"task_id": "task-sim-replacement", "status": "accepted"}]
                },
            },
        )

        failures = evaluate_case(case, result)

        self.assertTrue(
            any("replacement task" in failure.message for failure in failures)
        )


if __name__ == "__main__":
    unittest.main()
