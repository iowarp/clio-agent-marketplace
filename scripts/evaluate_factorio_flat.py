#!/usr/bin/env python3
"""Evaluate normalized Factorio Flat black-box traces against semantic cases.

The grader reads only what an observer of a live session can see: the public
response, the tool trace, and the runtime state the trace exposes. Every signal
it matches on is one the runtime actually produces.

* An ``AgentTask`` status is one of ``queued``, ``running``, ``completed``,
  ``failed``, ``cancelled`` — the set is closed, and the three terminal ones are
  immutable. There is no paused status.
* A child that needs a scientist-owned decision therefore stays ``running``. The
  runtime mints a FORWARDED ``UserQuestion`` on the attended (root) session whose
  ``owner_session_id`` is the child session, and flips that child session to
  ``waiting_user``. A blocked consultation is exactly that conjunction, and it is
  attributed to a task by joining the question's ``owner_session_id`` to the
  task's ``child_session_id``.

The grader asserts OUTCOMES — what the turn achieved — not turn structure. It
never dictates tool ordering, never caps how often a tool may be called, and
never carries a forbidden-tool blacklist: a case that must be answered directly
says so as an outcome (no children were spawned), and a case that must produce
substance says so as a floor on the answer, grounded in what the children
actually returned.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


# The runtime's closed status vocabularies. A trace using anything else is not a
# trace of this runtime, so it is rejected rather than graded.
TASK_STATUSES = frozenset({"queued", "running", "completed", "failed", "cancelled"})
TERMINAL_TASK_STATUSES = frozenset({"completed", "failed", "cancelled"})
QUESTION_STATUSES = frozenset({"pending", "answered", "cancelled", "expired"})

# The source the runtime stamps on a child question mirrored onto the parent.
FORWARDED_QUESTION_SOURCE = "child_forwarded"

SPAWN_ACTIONS = frozenset({"spawn_agent_task", "spawn_agents_parallel"})
COLLECT_ACTIONS = frozenset({"wait_agent_tasks", "check_agent_tasks"})

# A content term: long enough that sharing one between two texts is evidence of
# carried information rather than shared grammar.
_CONTENT_TERM = re.compile(r"[a-z][a-z0-9-]{5,}")


@dataclass(frozen=True)
class EvaluationFailure:
    """One failed semantic assertion for a behavioral case."""

    case_id: str
    message: str


@dataclass(frozen=True)
class TaskObservation:
    """One task status the trace shows the agent observing, in trace order."""

    index: int
    task_id: str
    status: str


def _content_terms(text: str) -> set[str]:
    """Return the distinctive terms of one text."""

    return set(_CONTENT_TERM.findall(str(text).lower()))


def _rows(value: Any) -> list[dict[str, Any]]:
    """Return the mapping rows of a JSON list, ignoring anything else."""

    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _actions(result: dict[str, Any], name: str) -> list[dict[str, Any]]:
    """Return normalized trace actions with the requested name."""

    return [action for action in _rows(result.get("actions")) if action.get("name") == name]


def _spawned_agents(result: dict[str, Any]) -> list[str]:
    """Return all declared-agent targets in trace order."""

    agents: list[str] = []
    for action in _rows(result.get("actions")):
        arguments = action.get("arguments")
        if not isinstance(arguments, dict):
            continue
        if action.get("name") == "spawn_agent_task":
            if agent := str(arguments.get("agent") or ""):
                agents.append(agent)
        elif action.get("name") == "spawn_agents_parallel":
            agents.extend(
                str(spawn["agent"])
                for spawn in _rows(arguments.get("spawns"))
                if spawn.get("agent")
            )
    return agents


def _loaded_skills(result: dict[str, Any]) -> list[str]:
    """Return skill ids loaded by the trace."""

    return [
        str(action["arguments"]["skill_id"])
        for action in _actions(result, "load_skill")
        if isinstance(action.get("arguments"), dict) and action["arguments"].get("skill_id")
    ]


def _task_roster(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return the session's AgentTask records keyed by task id."""

    return {str(row["task_id"]): row for row in _rows(result.get("tasks")) if row.get("task_id")}


def _spawn_events(result: dict[str, Any]) -> list[tuple[int, str, str]]:
    """Return ``(trace index, agent, task id)`` for every spawn the trace made.

    ``spawn_agent_task`` returns one handle; ``spawn_agents_parallel`` returns a
    ``spawned`` list of them in request order.
    """

    events: list[tuple[int, str, str]] = []
    for index, action in enumerate(_rows(result.get("actions"))):
        name = action.get("name")
        if name not in SPAWN_ACTIONS:
            continue
        arguments = action.get("arguments") if isinstance(action.get("arguments"), dict) else {}
        payload = action.get("result") if isinstance(action.get("result"), dict) else {}
        if name == "spawn_agent_task":
            events.append(
                (index, str(arguments.get("agent") or ""), str(payload.get("task_id") or ""))
            )
            continue
        spawns = _rows(arguments.get("spawns"))
        for offset, handle in enumerate(_rows(payload.get("spawned"))):
            agent = str(spawns[offset].get("agent") or "") if offset < len(spawns) else ""
            events.append((index, agent, str(handle.get("task_id") or "")))
    return events


def _collected_rows(result: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    """Return ``(trace index, row)`` for every task row a collector returned.

    ``wait_agent_tasks`` returns full-fidelity ``results`` rows; ``check_agent_tasks``
    returns compact ``tasks`` rows. Both are read, so a poll counts as an
    observation exactly like a blocking wait.
    """

    collected: list[tuple[int, dict[str, Any]]] = []
    for index, action in enumerate(_rows(result.get("actions"))):
        if action.get("name") not in COLLECT_ACTIONS:
            continue
        payload = action.get("result") if isinstance(action.get("result"), dict) else {}
        for row in _rows(payload.get("results")) + _rows(payload.get("tasks")):
            if row.get("task_id"):
                collected.append((index, row))
    return collected


def _task_observations(result: dict[str, Any]) -> list[TaskObservation]:
    """Return every task status the trace shows, in trace order."""

    return [
        TaskObservation(index=index, task_id=str(row["task_id"]), status=str(row.get("status", "")))
        for index, row in _collected_rows(result)
    ]


def _returned_output(row: dict[str, Any]) -> str:
    """Return what a collected task row carried back from the child."""

    nested = row.get("result") if isinstance(row.get("result"), dict) else {}
    return str(row.get("output") or nested.get("answer_excerpt") or "")


def _forwarded_child_sessions(result: dict[str, Any]) -> set[str]:
    """Return the child sessions that owned a question forwarded to the parent.

    A question the attended session owns itself (``owner_session_id`` equals
    ``attended_session_id``) is the root asking on its own behalf, never a
    blocked child.
    """

    return {
        str(question["owner_session_id"])
        for question in _rows(result.get("questions"))
        if question.get("source") == FORWARDED_QUESTION_SOURCE
        and question.get("owner_session_id")
        and question.get("owner_session_id") != question.get("attended_session_id")
    }


def _observed_session_statuses(result: dict[str, Any]) -> dict[str, set[str]]:
    """Return every status each session was observed holding during the run."""

    statuses: dict[str, set[str]] = {}
    for row in _rows(result.get("sessions")):
        if session_id := str(row.get("session_id") or ""):
            statuses.setdefault(session_id, set()).add(str(row.get("status", "")))
    return statuses


def _check_shape(case_id: str, result: dict[str, Any]) -> list[EvaluationFailure]:
    """Reject a normalized trace the grader cannot read.

    A missing key is not an empty one: a trace with no ``actions`` block records
    nothing about what the agent did, and grading it as compliant is how a broken
    adapter passes every case.
    """

    failures: list[EvaluationFailure] = []
    if not isinstance(result.get("response"), str):
        failures.append(EvaluationFailure(case_id, "trace field response must be a string"))
    for key in ("actions", "tasks", "questions", "sessions"):
        if not isinstance(result.get(key), list):
            failures.append(EvaluationFailure(case_id, f"trace field {key} must be a list"))
    if failures:
        return failures

    for action in result["actions"]:
        if not isinstance(action, dict) or not str(action.get("name") or ""):
            failures.append(EvaluationFailure(case_id, "each action needs a name"))
        elif not isinstance(action.get("arguments", {}), dict):
            failures.append(
                EvaluationFailure(case_id, f"action {action['name']} arguments must be an object")
            )
    for row in result["tasks"]:
        if not isinstance(row, dict) or not str(row.get("task_id") or ""):
            failures.append(EvaluationFailure(case_id, "each task row needs a task_id"))
            continue
        for field in ("agent", "child_session_id"):
            if not str(row.get(field) or ""):
                failures.append(
                    EvaluationFailure(case_id, f"task {row['task_id']} is missing {field}")
                )
        status = str(row.get("status", ""))
        if status not in TASK_STATUSES:
            failures.append(
                EvaluationFailure(
                    case_id,
                    f"task {row['task_id']} reports status {status!r}, which the runtime "
                    f"cannot produce (statuses: {', '.join(sorted(TASK_STATUSES))})",
                )
            )
    for question in result["questions"]:
        if not isinstance(question, dict) or not str(question.get("id") or ""):
            failures.append(EvaluationFailure(case_id, "each question row needs an id"))
            continue
        for field in ("owner_session_id", "attended_session_id", "source"):
            if not str(question.get(field) or ""):
                failures.append(
                    EvaluationFailure(case_id, f"question {question['id']} is missing {field}")
                )
        status = str(question.get("status", ""))
        if status not in QUESTION_STATUSES:
            failures.append(
                EvaluationFailure(
                    case_id,
                    f"question {question['id']} reports status {status!r}, which the runtime "
                    f"cannot produce (statuses: {', '.join(sorted(QUESTION_STATUSES))})",
                )
            )
    for row in result["sessions"]:
        if not isinstance(row, dict) or not str(row.get("session_id") or ""):
            failures.append(EvaluationFailure(case_id, "each session row needs a session_id"))
    return failures


def _check_response(
    case_id: str, expectation: dict[str, Any], result: dict[str, Any]
) -> list[EvaluationFailure]:
    """Check response-shape floors and ceilings without matching exact prose."""

    failures: list[EvaluationFailure] = []
    response = str(result.get("response") or "").strip()
    words = len(response.split())
    if expectation.get("nonempty") and not response:
        failures.append(EvaluationFailure(case_id, "response must be nonempty"))
    min_words = expectation.get("min_words")
    if isinstance(min_words, int) and words < min_words:
        failures.append(
            EvaluationFailure(case_id, f"response has {words} words, below the floor of {min_words}")
        )
    max_words = expectation.get("max_words")
    if isinstance(max_words, int) and words > max_words:
        failures.append(EvaluationFailure(case_id, f"response exceeds {max_words} words"))
    return failures


def _check_actions(
    case_id: str, expectation: dict[str, Any], result: dict[str, Any]
) -> list[EvaluationFailure]:
    """Check that the capabilities a case genuinely needs were reached for.

    Required only: a blacklist of tools the agent must not touch dictates turn
    structure rather than outcome, so what a case must NOT do is asserted through
    :func:`_check_outcome` instead.
    """

    names = {str(action.get("name")) for action in _rows(result.get("actions"))}
    return [
        EvaluationFailure(case_id, f"required action missing: {name}")
        for name in expectation.get("required", [])
        if name not in names
    ]


def _check_question(
    case_id: str, expectation: dict[str, Any], result: dict[str, Any]
) -> list[EvaluationFailure]:
    """Check that clarification calls are focused and decision-useful."""

    failures: list[EvaluationFailure] = []
    questions = _actions(result, "ask_user")
    if len(questions) < int(expectation.get("min_count", 0)):
        failures.append(EvaluationFailure(case_id, "too few clarification questions"))
    for action in questions:
        arguments = action.get("arguments")
        if not isinstance(arguments, dict):
            failures.append(EvaluationFailure(case_id, "ask_user arguments must be an object"))
            continue
        if expectation.get("requires_question") and not str(arguments.get("question") or "").strip():
            failures.append(EvaluationFailure(case_id, "ask_user needs a concrete question"))
        if expectation.get("requires_reason") and not str(arguments.get("reason") or "").strip():
            failures.append(EvaluationFailure(case_id, "ask_user needs scientific consequence"))
    return failures


def _check_coordination(
    case_id: str, expectation: dict[str, Any], result: dict[str, Any]
) -> list[EvaluationFailure]:
    """Check focused skill selection and delegation shape."""

    failures: list[EvaluationFailure] = []
    loaded = _loaded_skills(result)
    failures.extend(
        EvaluationFailure(case_id, f"required skill not loaded: {skill}")
        for skill in expectation.get("required_skills", [])
        if skill not in loaded
    )

    expected_agents = expectation.get("exact_agents")
    spawned = _spawned_agents(result)
    if isinstance(expected_agents, list) and sorted(spawned) != sorted(expected_agents):
        failures.append(
            EvaluationFailure(
                case_id, f"spawned agents {spawned!r} do not match {expected_agents!r}"
            )
        )

    if expectation.get("requires_parallel"):
        width = max(
            (
                len(_rows(action["arguments"].get("spawns")))
                for action in _actions(result, "spawn_agents_parallel")
                if isinstance(action.get("arguments"), dict)
            ),
            default=0,
        )
        if width < int(expectation.get("min_parallel_width", 2)):
            failures.append(EvaluationFailure(case_id, "independent work was not fanned out"))
    return failures


def _check_outcome(
    case_id: str, case: dict[str, Any], expectation: dict[str, Any], result: dict[str, Any]
) -> list[EvaluationFailure]:
    """Check what the turn achieved: who ran, how they ended, and what was said."""

    failures: list[EvaluationFailure] = []
    roster = _task_roster(result)

    if expectation.get("no_children"):
        if roster:
            failures.append(
                EvaluationFailure(
                    case_id,
                    "expected a direct answer, but the turn ran children: "
                    + ", ".join(sorted(roster)),
                )
            )
        if spawns := _spawn_events(result):
            failures.append(
                EvaluationFailure(
                    case_id,
                    "expected a direct answer, but the turn called "
                    + ", ".join(sorted({agent for _, agent, _ in spawns if agent})),
                )
            )

    collected = _collected_rows(result)
    if expectation.get("children_completed"):
        if not roster:
            failures.append(
                EvaluationFailure(case_id, "the case needs consulted work, but no child ran")
            )
        for task_id, row in sorted(roster.items()):
            status = str(row.get("status", ""))
            if status == "completed":
                continue
            reason = str(row.get("error_reason") or "")
            failures.append(
                EvaluationFailure(
                    case_id,
                    f"child {task_id} ({row.get('agent', '?')}) ended {status}"
                    + (f" ({reason})" if reason else "")
                    + ", so the answer rests on work that never finished",
                )
            )
        uncollected = sorted(set(roster) - {str(row["task_id"]) for _, row in collected})
        if uncollected:
            failures.append(
                EvaluationFailure(
                    case_id, "spawned work was never collected: " + ", ".join(uncollected)
                )
            )

    if expectation.get("grounds_collected_results"):
        minimum = int(expectation.get("min_shared_terms", 2))
        response_terms = _content_terms(result.get("response", ""))
        # Terms the scientist already supplied prove nothing about grounding, so
        # only what a child ADDED counts toward the floor.
        asked_terms = _content_terms(case.get("user_message", ""))
        outputs = _completed_outputs(collected)
        # Iterate the ROSTER, not just what carried an output: a completed child
        # whose collected row returned nothing must fail the floor rather than
        # silently drop out of it.
        for task_id in sorted(task for task, row in roster.items() if row.get("status") == "completed"):
            output = outputs.get(task_id, "")
            if not output:
                failures.append(
                    EvaluationFailure(
                        case_id,
                        f"{task_id} completed but returned no output to ground the answer in",
                    )
                )
                continue
            contributed = _content_terms(output) - asked_terms
            shared = contributed & response_terms
            if len(shared) < minimum:
                failures.append(
                    EvaluationFailure(
                        case_id,
                        f"the answer is not grounded in what {task_id} returned "
                        f"({len(shared)} of {minimum} required shared terms)",
                    )
                )
    return failures


def _completed_outputs(collected: Iterable[tuple[int, dict[str, Any]]]) -> dict[str, str]:
    """Return the longest returned output per completed task the trace collected."""

    outputs: dict[str, str] = {}
    for _, row in collected:
        if str(row.get("status", "")) != "completed":
            continue
        output = _returned_output(row)
        task_id = str(row["task_id"])
        if len(output) > len(outputs.get(task_id, "")):
            outputs[task_id] = output
    return {task_id: output for task_id, output in outputs.items() if output}


def _check_blocked_child(
    case_id: str, expectation: dict[str, Any], result: dict[str, Any]
) -> list[EvaluationFailure]:
    """Check pause/resume continuity for a child that needed the scientist.

    A blocked consultation is a task the trace observed ``running`` whose child
    session owns a question forwarded to the attended parent. Both halves are
    required: the forwarded question alone could belong to a child that already
    finished, and a running task alone is just work in flight.
    """

    failures: list[EvaluationFailure] = []
    roster = _task_roster(result)
    forwarded_owners = _forwarded_child_sessions(result)
    attributed = {
        task_id: row
        for task_id, row in roster.items()
        if str(row.get("child_session_id") or "") in forwarded_owners
    }
    if not attributed:
        failures.append(
            EvaluationFailure(
                case_id,
                "no question was forwarded from a spawned child session, so no "
                "consultation ever asked the scientist directly",
            )
        )
        return failures

    observations = _task_observations(result)
    blocked: dict[str, int] = {}
    for observation in observations:
        if observation.task_id in attributed and observation.status == "running":
            blocked.setdefault(observation.task_id, observation.index)
    if not blocked:
        failures.append(
            EvaluationFailure(
                case_id,
                "the child that owns the forwarded question was never observed running, "
                "so the pause was never seen",
            )
        )
        return failures

    session_statuses = _observed_session_statuses(result)
    for task_id in sorted(blocked):
        child_session = str(attributed[task_id]["child_session_id"])
        if "waiting_user" not in session_statuses.get(child_session, set()):
            failures.append(
                EvaluationFailure(
                    case_id,
                    f"child session {child_session} was never observed waiting_user, so "
                    f"{task_id} never paused for the scientist",
                )
            )

    if expectation.get("same_identity_resume"):
        for task_id, blocked_at in sorted(blocked.items()):
            resumed = any(
                observation.task_id == task_id
                and observation.status == "completed"
                and observation.index > blocked_at
                for observation in observations
            )
            if not resumed:
                failures.append(
                    EvaluationFailure(
                        case_id,
                        f"{task_id} paused for the scientist but never completed under the "
                        "same task id after the answer",
                    )
                )

    if expectation.get("forbid_replacement"):
        for task_id, blocked_at in sorted(blocked.items()):
            agent = str(attributed[task_id].get("agent") or "")
            for index, spawn_agent, spawn_task_id in _spawn_events(result):
                if index > blocked_at and spawn_agent == agent and spawn_task_id != task_id:
                    failures.append(
                        EvaluationFailure(
                            case_id,
                            f"{task_id} was paused, but {spawn_agent} was spawned again as "
                            f"{spawn_task_id}: the consultation was replaced, not resumed",
                        )
                    )
    return failures


def evaluate_case(case: dict[str, Any], result: dict[str, Any]) -> list[EvaluationFailure]:
    """Evaluate one normalized black-box result against one semantic case."""

    case_id = str(case.get("id") or "<missing>")
    expect = case.get("expect", {})
    if not isinstance(expect, dict):
        return [EvaluationFailure(case_id, "expect must be an object")]
    # A trace the grader cannot read is not graded: every semantic check below
    # would otherwise read a missing key as an empty one and report a pass.
    if shape_failures := _check_shape(case_id, result):
        return shape_failures

    failures: list[EvaluationFailure] = []
    if isinstance(expect.get("response"), dict):
        failures.extend(_check_response(case_id, expect["response"], result))
    if isinstance(expect.get("actions"), dict):
        failures.extend(_check_actions(case_id, expect["actions"], result))
    if isinstance(expect.get("question"), dict):
        failures.extend(_check_question(case_id, expect["question"], result))
    if isinstance(expect.get("coordination"), dict):
        failures.extend(_check_coordination(case_id, expect["coordination"], result))
    if isinstance(expect.get("blocked_child"), dict):
        failures.extend(_check_blocked_child(case_id, expect["blocked_child"], result))
    if isinstance(expect.get("outcome"), dict):
        failures.extend(_check_outcome(case_id, case, expect["outcome"], result))
    return failures


def evaluate_files(cases_path: Path, results_path: Path) -> list[EvaluationFailure]:
    """Evaluate result records keyed by case id from two JSON files."""

    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    results = json.loads(results_path.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not isinstance(results, list):
        raise ValueError("cases and results must each be a JSON array")
    results_by_id = {
        str(result.get("case_id")): result for result in results if isinstance(result, dict)
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
