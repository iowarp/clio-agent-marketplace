"""Black-box semantic evals for Factorio Flat conversations and traces.

The evaluator reads only public output and REAL runtime signals, so these tests
sabotage the fixture with the failures the grader has to catch: a trace shape it
cannot read, a status the runtime cannot produce, an answer with no substance, a
child that ended `failed`, an answer ungrounded in what the children returned,
and a paused consultation replaced instead of resumed.
"""

from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any

from scripts.evaluate_factorio_flat import evaluate_case, evaluate_files


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "factorio-flat" / "evals" / "behavioral-cases.json"
RESULTS = ROOT / "tests" / "fixtures" / "factorio-flat-behavioral-results.json"


def _pair(case_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return one case and a deep copy of its reference trace, ready to sabotage."""

    cases = json.loads(CASES.read_text(encoding="utf-8"))
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    case = next(item for item in cases if item["id"] == case_id)
    result = next(item for item in results if item["case_id"] == case_id)
    return case, deepcopy(result)


def _action(result: dict[str, Any], name: str) -> dict[str, Any]:
    """Return the first action with ``name`` from a normalized trace."""

    return next(action for action in result["actions"] if action["name"] == name)


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


class FactorioFlatTraceShapeTests(unittest.TestCase):
    """An untrustworthy trace must be rejected, never graded as compliant."""

    def test_a_trace_missing_the_actions_key_is_rejected(self) -> None:
        """A trace with no observable actions cannot satisfy any case."""

        case, result = _pair("greeting")
        del result["actions"]

        failures = evaluate_case(case, result)

        self.assertTrue(any("actions" in failure.message for failure in failures))

    def test_a_trace_missing_the_task_roster_is_rejected(self) -> None:
        """Outcome grading needs the task roster; its absence is not a pass."""

        case, result = _pair("focused_skill_and_delegation")
        del result["tasks"]

        failures = evaluate_case(case, result)

        self.assertTrue(any("tasks" in failure.message for failure in failures))

    def test_a_status_the_runtime_cannot_produce_is_rejected(self) -> None:
        """AgentTask statuses are closed: queued/running/completed/failed/cancelled."""

        case, result = _pair("blocked_child_resume")
        result["tasks"][0]["status"] = "needs_input"

        failures = evaluate_case(case, result)

        self.assertTrue(any("needs_input" in failure.message for failure in failures))

    def test_a_question_status_the_runtime_cannot_produce_is_rejected(self) -> None:
        """UserQuestion statuses are closed: pending/answered/cancelled/expired."""

        case, result = _pair("blocked_child_resume")
        result["questions"][0]["status"] = "blocked"

        failures = evaluate_case(case, result)

        self.assertTrue(any("blocked" in failure.message for failure in failures))


class FactorioFlatOutcomeTests(unittest.TestCase):
    """A case passes on what the turn achieved, not on which tools were named."""

    def test_a_contentless_answer_fails_a_direct_answer_case(self) -> None:
        """'ok' is a response string, not an answer to a scientific question."""

        case, result = _pair("simple_question")
        result["response"] = "ok"

        failures = evaluate_case(case, result)

        self.assertTrue(any("words" in failure.message for failure in failures))

    def test_a_contentless_greeting_reply_fails(self) -> None:
        """Even the cheapest case has a floor below which nothing was said."""

        case, result = _pair("greeting")
        result["response"] = "ok"

        failures = evaluate_case(case, result)

        self.assertTrue(any("words" in failure.message for failure in failures))

    def test_unnecessary_delegation_fails_a_direct_answer_case(self) -> None:
        """Direct scientific questions must not trigger coordinator overhead."""

        case, result = _pair("simple_question")
        result["actions"].append(
            {
                "name": "spawn_agent_task",
                "arguments": {"agent": "research_methodologist", "task": "Define stress."},
                "result": {"task_id": "task_unnecessary", "status": "running", "run_index": 0},
            }
        )
        result["tasks"].append(
            {
                "task_id": "task_unnecessary",
                "agent": "research_methodologist",
                "child_session_id": "sess_child_unnecessary",
                "status": "completed",
                "error_reason": "",
            }
        )

        failures = evaluate_case(case, result)

        self.assertTrue(any("direct answer" in failure.message for failure in failures))

    def test_a_failed_child_fails_a_delegation_case(self) -> None:
        """A case answered over children that all failed is not a pass."""

        case, result = _pair("parallel_investigation")
        for row in result["tasks"]:
            row["status"] = "failed"
            row["error_reason"] = "agent_error"
        for row in _action(result, "wait_agent_tasks")["result"]["results"]:
            row["status"] = "failed"
            row["error_reason"] = "agent_error"

        failures = evaluate_case(case, result)

        self.assertTrue(any("failed" in failure.message for failure in failures))

    def test_one_failed_child_among_several_fails_the_case(self) -> None:
        """A partial failure is still work the synthesis cannot rest on."""

        case, result = _pair("parallel_investigation")
        result["tasks"][1]["status"] = "failed"
        result["tasks"][1]["error_reason"] = "timeout"

        failures = evaluate_case(case, result)

        self.assertTrue(any("task_lab_1" in failure.message for failure in failures))

    def test_a_child_that_returned_nothing_cannot_ground_the_answer(self) -> None:
        """A completed child with an empty output must fail the grounding floor."""

        case, result = _pair("focused_skill_and_delegation")
        for row in _action(result, "wait_agent_tasks")["result"]["results"]:
            row["output"] = ""

        failures = evaluate_case(case, result)

        self.assertTrue(any("no output" in failure.message for failure in failures))

    def test_an_answer_ungrounded_in_child_results_fails(self) -> None:
        """The synthesis must carry what the consultations actually returned."""

        case, result = _pair("parallel_investigation")
        result["response"] = (
            "I looked into both questions and the overall picture seems broadly "
            "reasonable, so we should probably keep going with the current plan."
        )

        failures = evaluate_case(case, result)

        self.assertTrue(any("grounded" in failure.message for failure in failures))


class FactorioFlatBlockedChildTests(unittest.TestCase):
    """A paused consultation is a running task plus a forwarded child question."""

    def test_replacing_a_blocked_child_fails_the_resume_case(self) -> None:
        """A replacement consultation loses the original's context and provenance."""

        case, result = _pair("blocked_child_resume")
        result["actions"][-1:] = [
            {
                "name": "spawn_agent_task",
                "arguments": {
                    "agent": "simulation_methodologist",
                    "task": "Redo the formulation with the fixture answer.",
                },
                "result": {"task_id": "task_sim_99", "status": "running", "run_index": 0},
            },
            {
                "name": "wait_agent_tasks",
                "arguments": {"task_ids": ["task_sim_99"], "timeout_s": 120},
                "result": {
                    "results": [
                        {
                            "agent_id": "simulation_methodologist",
                            "parent_id": "main",
                            "task_id": "task_sim_99",
                            "run_index": 0,
                            "status": "completed",
                            "stage": "delegate.completed",
                            "output": "With the lower fixture free to translate axially, the "
                            "formulation uses a sliding contact and the axial-translation "
                            "choice is recorded as scientist-supplied. Mesh refinement at "
                            "the fillet governs the reported stress concentration.",
                            "message_ref": "msg_sim_99",
                            "error_reason": "",
                        }
                    ],
                    "workflow_state_conflicts": [],
                    "merged_workflow_state": {},
                },
            },
        ]
        result["tasks"][0]["status"] = "cancelled"
        result["tasks"].append(
            {
                "task_id": "task_sim_99",
                "agent": "simulation_methodologist",
                "child_session_id": "sess_child_sim_99",
                "status": "completed",
                "error_reason": "",
            }
        )

        failures = evaluate_case(case, result)
        messages = [failure.message for failure in failures]

        self.assertTrue(any("replace" in message for message in messages), messages)
        self.assertTrue(any("same task id" in message for message in messages), messages)

    def test_a_root_owned_question_is_not_a_blocked_child(self) -> None:
        """Attribution is the question owner joined to the task's child session."""

        case, result = _pair("blocked_child_resume")
        question = result["questions"][0]
        question["owner_session_id"] = question["attended_session_id"]
        question["source"] = "orchestrator"
        question["metadata"] = {}

        failures = evaluate_case(case, result)

        self.assertTrue(any("forwarded" in failure.message for failure in failures))

    def test_a_child_never_observed_waiting_user_fails_the_resume_case(self) -> None:
        """The paused child session is the runtime signal that it asked at all."""

        case, result = _pair("blocked_child_resume")
        result["sessions"] = [
            row for row in result["sessions"] if row["session_id"] != "sess_child_sim_42"
        ]

        failures = evaluate_case(case, result)

        self.assertTrue(any("waiting_user" in failure.message for failure in failures))

    def test_a_child_never_observed_running_fails_the_resume_case(self) -> None:
        """A consultation that was never seen in flight was never resumed either."""

        case, result = _pair("blocked_child_resume")
        result["actions"] = [
            action for action in result["actions"] if action["name"] != "check_agent_tasks"
        ]

        failures = evaluate_case(case, result)

        self.assertTrue(any("running" in failure.message for failure in failures))


if __name__ == "__main__":
    unittest.main()
