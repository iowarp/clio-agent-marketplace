#!/usr/bin/env python3
"""Evaluate normalized APPL-CORE Analyst black-box traces against semantic cases.

Skeleton grader, modelled on ``scripts/evaluate_factorio_flat.py``: it reads
only what an observer of a live session can see -- the public response, the
tool trace, the runtime rows (tasks, questions, sessions) -- plus a ``bundle``
record the capture adapter takes after the turn from the workspace store
(``<workspace_state>/datasets/<key>/``: the card text and the view hashes
of each loader run). It asserts OUTCOMES, not
turn structure: no tool ordering except where the outcome IS an order (the
parent re-runs a child's loader after collecting the child), no call caps.

Known limits, stated plainly:

* ``terms_any`` checks on the response and on questions are a lexical floor
  (any listed term appears, case-insensitive). They reject answers that never
  mention the subject; they cannot tell a good explanation from a bad one.
* Trap classes are read from the card's ``[trap:<class>]`` tags. The grader
  checks that the agent recorded a trap of that class, not that the line is
  right; a reader compares cards against the known trap list.
* Everything is validated against hand-written fixtures in the pack's tests;
  qualification needs traces from live sessions.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TASK_STATUSES = frozenset({"queued", "running", "completed", "failed", "cancelled"})
QUESTION_STATUSES = frozenset({"pending", "answered", "cancelled", "expired"})
REQUIRED_KEYS: dict[str, type] = {
    "response": str,
    "actions": list,
    "tasks": list,
    "questions": list,
    "sessions": list,
    "bundle": dict,
}
PROFILING_SCRIPTS = (
    "inventory.py",
    "audit_columns.py",
    "join_keys.py",
    "flag_check.py",
)
_TAGGED_CLAIM = re.compile(r"^\s*-\s*\[(stated|checked|inferred)\]", re.MULTILINE)
_TRAP = re.compile(r"\[trap:([a-z0-9-]+)\]")
_SECTION = re.compile(r"^## (.+)$", re.MULTILINE)
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
#: Namespaced dataset views, including legacy traces retained for comparison.
_VIEW_PATH = re.compile(r"/(?:datasets/[^/]+|\.clio(?:/datasets/[^/]+)?)/views/")


@dataclass(frozen=True)
class EvaluationFailure:
    """One failed semantic assertion for a behavioral case."""

    case_id: str
    message: str


def trap_classes() -> frozenset[str]:
    """The card vocabulary, read from the onboard-dataset card script."""

    path = (
        Path(__file__).resolve().parents[2] / "skills" / "onboard-dataset" / "scripts" / "card.py"
    )
    spec = importlib.util.spec_from_file_location("appl_core_card", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return frozenset(module.TRAP_CLASSES)


def _rows(value: Any) -> list[dict[str, Any]]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _commands(result: dict[str, Any]) -> list[tuple[int, str]]:
    """``(index, command)`` for every shell action, in trace order."""

    out = []
    for index, action in enumerate(_rows(result.get("actions"))):
        if action.get("name") == "shell_bash" and isinstance(action.get("arguments"), dict):
            out.append((index, str(action["arguments"].get("command", ""))))
    return out


def _skills_used(result: dict[str, Any]) -> set[str]:
    used = set()
    for action in _rows(result.get("actions")):
        arguments = action.get("arguments")
        if (
            action.get("name") in {"load_skill", "spawn_skill_task"}
            and isinstance(arguments, dict)
            and arguments.get("skill_id")
        ):
            used.add(str(arguments["skill_id"]))
    return used


def card_sections(card_text: str) -> dict[str, str]:
    """Section title -> body text with HTML comments removed."""

    text = _COMMENT.sub("", card_text)
    matches = list(_SECTION.finditer(text))
    sections = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[match.end() : end]
    return sections


def _check_shape(case_id: str, result: dict[str, Any]) -> list[EvaluationFailure]:
    failures = []
    for key, kind in REQUIRED_KEYS.items():
        if not isinstance(result.get(key), kind):
            failures.append(
                EvaluationFailure(case_id, f"trace key {key!r} missing or not a {kind.__name__}")
            )
    if failures:
        return failures
    for task in _rows(result["tasks"]):
        if task.get("status") not in TASK_STATUSES:
            failures.append(
                EvaluationFailure(
                    case_id,
                    f"task status {task.get('status')!r} is not a runtime status",
                )
            )
    for question in _rows(result["questions"]):
        if question.get("status") not in QUESTION_STATUSES:
            failures.append(
                EvaluationFailure(
                    case_id,
                    f"question status {question.get('status')!r} is not a runtime status",
                )
            )
    runs = result["bundle"].get("view_hash_runs", [])
    if not isinstance(runs, list) or not all(isinstance(run, dict) for run in runs):
        failures.append(
            EvaluationFailure(
                case_id,
                "bundle.view_hash_runs must be a list of {path: sha256} objects",
            )
        )
    return failures


def _check_response(
    case_id: str, expect: dict[str, Any], result: dict[str, Any]
) -> list[EvaluationFailure]:
    failures = []
    response = result["response"]
    words = len(response.split())
    if expect.get("nonempty") and not response.strip():
        failures.append(EvaluationFailure(case_id, "empty response"))
    if words < int(expect.get("min_words", 0)):
        failures.append(
            EvaluationFailure(case_id, f"response has {words} words, below {expect['min_words']}")
        )
    if "max_words" in expect and words > int(expect["max_words"]):
        failures.append(
            EvaluationFailure(case_id, f"response has {words} words, above {expect['max_words']}")
        )
    terms = [str(t).lower() for t in expect.get("terms_any", [])]
    if terms and not any(term in response.lower() for term in terms):
        failures.append(EvaluationFailure(case_id, f"response mentions none of {terms}"))
    return failures


def _check_actions(
    case_id: str, expect: dict[str, Any], result: dict[str, Any]
) -> list[EvaluationFailure]:
    failures = []
    names = {str(a.get("name")) for a in _rows(result["actions"])}
    for name in expect.get("required", []):
        if name not in names:
            failures.append(EvaluationFailure(case_id, f"required action {name!r} never ran"))
    used = _skills_used(result)
    for skill in expect.get("required_skills", []):
        if skill not in used:
            failures.append(
                EvaluationFailure(case_id, f"skill {skill!r} was never loaded or spawned")
            )
    commands = " ".join(command for _, command in _commands(result))
    for script in expect.get("required_scripts", []):
        if script not in commands:
            failures.append(EvaluationFailure(case_id, f"script {script!r} never ran"))
    return failures


def _check_card(
    case_id: str,
    expect: dict[str, Any],
    result: dict[str, Any],
    vocabulary: frozenset[str],
) -> list[EvaluationFailure]:
    failures = []
    card = result["bundle"].get("card_text")
    if expect.get("exists") and not isinstance(card, str):
        return [EvaluationFailure(case_id, "no experiment card was written")]
    if not isinstance(card, str):
        return failures
    claims = len(_TAGGED_CLAIM.findall(_COMMENT.sub("", card)))
    if claims < int(expect.get("min_tagged_claims", 0)):
        failures.append(
            EvaluationFailure(
                case_id,
                f"card has {claims} tagged claims, below {expect['min_tagged_claims']}",
            )
        )
    found = set(_TRAP.findall(_COMMENT.sub("", card)))
    unknown = found - vocabulary
    if unknown:
        failures.append(
            EvaluationFailure(
                case_id,
                f"card uses trap classes outside the vocabulary: {sorted(unknown)}",
            )
        )
    for trap in expect.get("required_trap_classes", []):
        if trap not in found:
            failures.append(EvaluationFailure(case_id, f"card records no [trap:{trap}]"))
    sections = card_sections(card)
    questions = [
        line
        for line in sections.get("Open questions for data owners", "").splitlines()
        if line.strip().startswith("- ")
    ]
    if len(questions) < int(expect.get("min_open_questions", 0)):
        failures.append(
            EvaluationFailure(
                case_id,
                f"card lists {len(questions)} open questions, below {expect['min_open_questions']}",
            )
        )
    return failures


def _check_loader(
    case_id: str, expect: dict[str, Any], result: dict[str, Any]
) -> list[EvaluationFailure]:
    failures = []
    runs = [run for run in result["bundle"].get("view_hash_runs", []) if run]
    if expect.get("deterministic"):
        if len(runs) < 2:
            failures.append(
                EvaluationFailure(
                    case_id,
                    f"loader ran {len(runs)} time(s) with outputs; determinism needs two",
                )
            )
        elif any(run != runs[0] for run in runs[1:]):
            failures.append(
                EvaluationFailure(case_id, "loader runs produced different view hashes")
            )
    if expect.get("verified"):
        verify = [c for _, c in _commands(result) if "card.py" in c and "verify" in c]
        codes = result["bundle"].get("verify_exit_codes", [])
        if not verify or 0 not in codes:
            failures.append(EvaluationFailure(case_id, "card.py verify never passed"))
    if expect.get("parent_reran_after_child"):
        waits = [
            i for i, a in enumerate(_rows(result["actions"])) if a.get("name") == "wait_agent_tasks"
        ]
        reruns = [i for i, c in _commands(result) if "loader.py" in c]
        if not waits or not any(i > waits[0] for i in reruns):
            failures.append(
                EvaluationFailure(
                    case_id,
                    "the parent never re-ran the loader after collecting the child",
                )
            )
    return failures


def _check_outcome(
    case_id: str, expect: dict[str, Any], result: dict[str, Any]
) -> list[EvaluationFailure]:
    failures = []
    commands = [c for _, c in _commands(result)]
    if expect.get("no_reprofile"):
        ran = sorted({s for s in PROFILING_SCRIPTS for c in commands if s in c})
        if ran:
            failures.append(
                EvaluationFailure(
                    case_id,
                    f"a current card existed but the session re-profiled with {ran}",
                )
            )
    if expect.get("no_views_written"):
        runs = [run for run in result["bundle"].get("view_hash_runs", []) if run]
        written = [
            p
            for p in result["bundle"].get("files_written", [])
            if _VIEW_PATH.search(str(p).replace("\\", "/"))
        ]
        if runs or written:
            failures.append(
                EvaluationFailure(
                    case_id,
                    "views were written for a bundle that should have been refused",
                )
            )
    if expect.get("children_completed") and not any(
        task.get("status") == "completed" for task in _rows(result["tasks"])
    ):
        failures.append(EvaluationFailure(case_id, "no child task completed"))
    return failures


def _check_question(
    case_id: str, expect: dict[str, Any], result: dict[str, Any]
) -> list[EvaluationFailure]:
    failures = []
    asked = [
        q
        for q in _rows(result["questions"])
        if q.get("source", "orchestrator") != "child_forwarded"
    ]
    if len(asked) < int(expect.get("min_count", 0)):
        failures.append(
            EvaluationFailure(case_id, f"{len(asked)} questions asked, below {expect['min_count']}")
        )
    terms = [str(t).lower() for t in expect.get("terms_any", [])]
    if (
        terms
        and asked
        and not any(term in str(q.get("prompt", "")).lower() for q in asked for term in terms)
    ):
        failures.append(EvaluationFailure(case_id, f"no question mentions any of {terms}"))
    return failures


def evaluate_case(
    case: dict[str, Any],
    result: dict[str, Any],
    vocabulary: frozenset[str] | None = None,
) -> list[EvaluationFailure]:
    """Evaluate one normalized result against one semantic case."""

    vocabulary = vocabulary if vocabulary is not None else trap_classes()
    case_id = str(case.get("id") or "<missing>")
    expect = case.get("expect", {})
    if not isinstance(expect, dict):
        return [EvaluationFailure(case_id, "expect must be an object")]
    if failures := _check_shape(case_id, result):
        return failures
    failures = []
    checks = {
        "response": _check_response,
        "actions": _check_actions,
        "loader": _check_loader,
        "outcome": _check_outcome,
        "question": _check_question,
    }
    for key, check in checks.items():
        if isinstance(expect.get(key), dict):
            failures.extend(check(case_id, expect[key], result))
    if isinstance(expect.get("card"), dict):
        failures.extend(_check_card(case_id, expect["card"], result, vocabulary))
    return failures


def validate_cases(
    cases: list[dict[str, Any]], vocabulary: frozenset[str] | None = None
) -> list[str]:
    """Static checks on the case file itself (unique ids, known trap classes)."""

    vocabulary = vocabulary if vocabulary is not None else trap_classes()
    problems = []
    ids = [str(case.get("id")) for case in cases]
    problems.extend(f"duplicate case id {i}" for i in sorted({i for i in ids if ids.count(i) > 1}))
    for case in cases:
        for trap in case.get("expect", {}).get("card", {}).get("required_trap_classes", []):
            if trap not in vocabulary:
                problems.append(f"{case.get('id')}: unknown trap class {trap}")
    return problems


def evaluate_files(cases_path: Path, results_path: Path) -> list[EvaluationFailure]:
    """Evaluate result records keyed by case id from two JSON files."""

    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    results = json.loads(results_path.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not isinstance(results, list):
        raise TypeError("cases and results must each be a JSON array")
    vocabulary = trap_classes()
    failures = [
        EvaluationFailure("<cases>", problem) for problem in validate_cases(cases, vocabulary)
    ]
    by_id = {str(r.get("case_id")): r for r in results if isinstance(r, dict)}
    for case in cases:
        case_id = str(case.get("id") or "<missing>")
        result = by_id.get(case_id)
        if result is None:
            failures.append(EvaluationFailure(case_id, "black-box result is missing"))
            continue
        failures.extend(evaluate_case(case, result, vocabulary))
    return failures


def main(argv: Sequence[str] | None = None) -> int:
    """Run the behavioral evaluator and return a process exit status."""

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("cases", type=Path)
    parser.add_argument("results", type=Path)
    args = parser.parse_args(argv)
    failures = evaluate_files(args.cases, args.results)
    if not failures:
        print("OK: APPL-CORE Analyst traces satisfy all semantic cases")
        return 0
    for failure in failures:
        print(f"{failure.case_id}: {failure.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
