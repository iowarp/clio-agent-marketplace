#!/usr/bin/env python3
"""Evaluate normalized Factorio Flat black-box traces against semantic cases."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class EvaluationFailure:
    """One failed semantic assertion for a behavioral case."""

    case_id: str
    message: str


def _actions(result: dict[str, Any], name: str) -> list[dict[str, Any]]:
    """Return normalized trace actions with the requested name."""

    return [
        action
        for action in result.get("actions", [])
        if isinstance(action, dict) and action.get("name") == name
    ]


def _spawned_agents(result: dict[str, Any]) -> list[str]:
    """Return all declared-agent targets in trace order."""

    agents: list[str] = []
    for action in result.get("actions", []):
        if not isinstance(action, dict):
            continue
        arguments = action.get("arguments", {})
        if not isinstance(arguments, dict):
            continue
        if action.get("name") == "spawn_agent_task":
            agent = str(arguments.get("agent") or "")
            if agent:
                agents.append(agent)
        elif action.get("name") == "spawn_agents_parallel":
            spawns = arguments.get("spawns", [])
            if isinstance(spawns, list):
                agents.extend(
                    str(spawn.get("agent"))
                    for spawn in spawns
                    if isinstance(spawn, dict) and spawn.get("agent")
                )
    return agents


def _loaded_skills(result: dict[str, Any]) -> list[str]:
    """Return skill ids loaded by the trace."""

    skills: list[str] = []
    for action in _actions(result, "load_skill"):
        arguments = action.get("arguments", {})
        if isinstance(arguments, dict) and arguments.get("skill_id"):
            skills.append(str(arguments["skill_id"]))
    return skills


def _task_rows(action: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized task result rows from one action."""

    result = action.get("result", {})
    if not isinstance(result, dict):
        return []
    tasks = result.get("tasks", [])
    return (
        [task for task in tasks if isinstance(task, dict)]
        if isinstance(tasks, list)
        else []
    )


def _check_response(
    case_id: str, expectation: dict[str, Any], result: dict[str, Any]
) -> list[EvaluationFailure]:
    """Check response-shape semantics without matching exact prose."""

    failures: list[EvaluationFailure] = []
    response = str(result.get("response") or "").strip()
    if expectation.get("nonempty") and not response:
        failures.append(EvaluationFailure(case_id, "response must be nonempty"))
    max_words = expectation.get("max_words")
    if isinstance(max_words, int) and len(response.split()) > max_words:
        failures.append(
            EvaluationFailure(case_id, f"response exceeds {max_words} words")
        )
    return failures


def _check_actions(
    case_id: str, expectation: dict[str, Any], result: dict[str, Any]
) -> list[EvaluationFailure]:
    """Check required and forbidden tool actions."""

    failures: list[EvaluationFailure] = []
    names = [
        str(action.get("name"))
        for action in result.get("actions", [])
        if isinstance(action, dict)
    ]
    for name in expectation.get("required", []):
        if name not in names:
            failures.append(
                EvaluationFailure(case_id, f"required action missing: {name}")
            )
    for name in expectation.get("forbidden", []):
        if name in names:
            failures.append(
                EvaluationFailure(case_id, f"forbidden action used: {name}")
            )
    return failures


def _check_question(
    case_id: str, expectation: dict[str, Any], result: dict[str, Any]
) -> list[EvaluationFailure]:
    """Check that clarification calls are focused and decision-useful."""

    failures: list[EvaluationFailure] = []
    questions = _actions(result, "ask_user")
    minimum = int(expectation.get("min_count", 0))
    maximum = expectation.get("max_count")
    if len(questions) < minimum:
        failures.append(EvaluationFailure(case_id, "too few clarification questions"))
    if isinstance(maximum, int) and len(questions) > maximum:
        failures.append(EvaluationFailure(case_id, "too many clarification questions"))
    for action in questions:
        arguments = action.get("arguments", {})
        if not isinstance(arguments, dict):
            failures.append(
                EvaluationFailure(case_id, "ask_user arguments must be an object")
            )
            continue
        if (
            expectation.get("requires_question")
            and not str(arguments.get("question") or "").strip()
        ):
            failures.append(
                EvaluationFailure(case_id, "ask_user needs a concrete question")
            )
        if (
            expectation.get("requires_reason")
            and not str(arguments.get("reason") or "").strip()
        ):
            failures.append(
                EvaluationFailure(case_id, "ask_user needs scientific consequence")
            )
    return failures


def _check_skill_and_spawn(
    case_id: str, expectation: dict[str, Any], result: dict[str, Any]
) -> list[EvaluationFailure]:
    """Check focused skill selection and delegation shape."""

    failures: list[EvaluationFailure] = []
    loaded = _loaded_skills(result)
    for skill in expectation.get("required_skills", []):
        if skill not in loaded:
            failures.append(
                EvaluationFailure(case_id, f"required skill not loaded: {skill}")
            )

    expected_agents = expectation.get("exact_agents")
    spawned = _spawned_agents(result)
    if isinstance(expected_agents, list) and sorted(spawned) != sorted(expected_agents):
        failures.append(
            EvaluationFailure(
                case_id,
                f"spawned agents {spawned!r} do not match {expected_agents!r}",
            )
        )

    if expectation.get("requires_parallel"):
        parallel = _actions(result, "spawn_agents_parallel")
        width = max(
            (
                len(action.get("arguments", {}).get("spawns", []))
                for action in parallel
                if isinstance(action.get("arguments"), dict)
                and isinstance(action["arguments"].get("spawns"), list)
            ),
            default=0,
        )
        if width < int(expectation.get("min_parallel_width", 2)):
            failures.append(
                EvaluationFailure(case_id, "independent work was not fanned out")
            )

    if expectation.get("skills_before_delegation"):
        actions = result.get("actions", [])
        spawn_indexes = [
            index
            for index, action in enumerate(actions)
            if isinstance(action, dict)
            and action.get("name") in {"spawn_agent_task", "spawn_agents_parallel"}
        ]
        skill_indexes = [
            index
            for index, action in enumerate(actions)
            if isinstance(action, dict) and action.get("name") == "load_skill"
        ]
        if spawn_indexes and not any(
            index < spawn_indexes[0] for index in skill_indexes
        ):
            failures.append(
                EvaluationFailure(case_id, "delegation preceded skill loading")
            )
    return failures


def _check_blocked_task(
    case_id: str, expectation: dict[str, Any], result: dict[str, Any]
) -> list[EvaluationFailure]:
    """Check pause/resume continuity for a child that needs user input."""

    failures: list[EvaluationFailure] = []
    waits = _actions(result, "wait_agent_tasks")
    blocked_ids = {
        str(task.get("task_id"))
        for wait in waits
        for task in _task_rows(wait)
        if task.get("status") in {"blocked", "needs_input"} and task.get("task_id")
    }
    completed_ids = {
        str(task.get("task_id"))
        for wait in waits
        for task in _task_rows(wait)
        if task.get("status") == "completed" and task.get("task_id")
    }
    if expectation.get("same_identity_resume") and not (blocked_ids & completed_ids):
        failures.append(
            EvaluationFailure(
                case_id, "blocked child did not resume with the same task id"
            )
        )

    child_questions = {
        str(action.get("actor_task_id"))
        for action in _actions(result, "ask_user")
        if action.get("actor_task_id")
    }
    if expectation.get("child_asks_directly") and not (blocked_ids & child_questions):
        failures.append(
            EvaluationFailure(case_id, "blocked child did not own its ask_user call")
        )

    if expectation.get("forbid_replacement"):
        spawned_ids = [
            str(row.get("task_id"))
            for action in result.get("actions", [])
            if isinstance(action, dict)
            and action.get("name") in {"spawn_agent_task", "spawn_agents_parallel"}
            for row in _task_rows(action)
            if row.get("task_id")
        ]
        for task_id in blocked_ids:
            if spawned_ids.count(task_id) > 1:
                failures.append(
                    EvaluationFailure(case_id, f"blocked child was replaced: {task_id}")
                )
        max_spawn_count = expectation.get("max_spawn_count")
        if isinstance(max_spawn_count, int) and len(spawned_ids) > max_spawn_count:
            failures.append(
                EvaluationFailure(case_id, "blocked child spawned a replacement task")
            )
    return failures


def evaluate_case(
    case: dict[str, Any], result: dict[str, Any]
) -> list[EvaluationFailure]:
    """Evaluate one normalized black-box result against one semantic case."""

    case_id = str(case.get("id") or "<missing>")
    expect = case.get("expect", {})
    if not isinstance(expect, dict):
        return [EvaluationFailure(case_id, "expect must be an object")]
    failures: list[EvaluationFailure] = []
    if isinstance(expect.get("response"), dict):
        failures.extend(_check_response(case_id, expect["response"], result))
    if isinstance(expect.get("actions"), dict):
        failures.extend(_check_actions(case_id, expect["actions"], result))
    if isinstance(expect.get("question"), dict):
        failures.extend(_check_question(case_id, expect["question"], result))
    if isinstance(expect.get("coordination"), dict):
        failures.extend(_check_skill_and_spawn(case_id, expect["coordination"], result))
    if isinstance(expect.get("blocked_task"), dict):
        failures.extend(_check_blocked_task(case_id, expect["blocked_task"], result))
    return failures


def evaluate_files(cases_path: Path, results_path: Path) -> list[EvaluationFailure]:
    """Evaluate result records keyed by case id from two JSON files."""

    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    results = json.loads(results_path.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not isinstance(results, list):
        raise ValueError("cases and results must each be a JSON array")
    results_by_id = {
        str(result.get("case_id")): result
        for result in results
        if isinstance(result, dict)
    }
    failures: list[EvaluationFailure] = []
    for case in cases:
        if not isinstance(case, dict):
            failures.append(EvaluationFailure("<missing>", "case must be an object"))
            continue
        case_id = str(case.get("id") or "<missing>")
        result = results_by_id.get(case_id)
        if result is None:
            failures.append(EvaluationFailure(case_id, "black-box result is missing"))
            continue
        failures.extend(evaluate_case(case, result))
    return failures


def main(argv: Sequence[str] | None = None) -> int:
    """Run the behavioral evaluator and return a process exit status."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path)
    parser.add_argument("results", type=Path)
    args = parser.parse_args(argv)
    failures = evaluate_files(args.cases, args.results)
    if not failures:
        print("OK: Factorio Flat behavioral traces satisfy all semantic cases")
        return 0
    for failure in failures:
        print(f"{failure.case_id}: {failure.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
