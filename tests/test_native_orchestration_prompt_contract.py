"""Marketplace prompts defer task waiting and observation to native contracts."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _model_instruction_files() -> list[Path]:
    return sorted(
        {
            *ROOT.glob("*/experts/**/*.md"),
            *ROOT.glob("*/skills/**/*.md"),
        }
    )


def test_model_instructions_do_not_reference_removed_or_bounded_task_collection() -> None:
    violations: list[str] = []
    for path in _model_instruction_files():
        text = path.read_text(encoding="utf-8")
        if "check_agent_tasks" in text:
            violations.append(f"{path.relative_to(ROOT)} references check_agent_tasks")
        for legacy in ("wait_agent_tasks", "observe_agent_tasks", "cancel_agent_task"):
            if legacy in text:
                violations.append(f"{path.relative_to(ROOT)} references legacy {legacy}")
        if re.search(r"wait_agent_tasks[^\n]{0,120}timeout_s", text):
            violations.append(f"{path.relative_to(ROOT)} gives wait_agent_tasks a timeout")

    assert violations == []


def test_consultation_question_guidance_keeps_question_and_assignment_separate() -> None:
    """A declined or unanswered Question must not be described as a child failure."""
    text = (
        ROOT / "factorio-flat/skills/coordinate-scientific-work/references/task-lifecycle.md"
    ).read_text(encoding="utf-8")
    assert "separate Question handle" in text and "wait_tasks(question_handle)" in text
    assert "does not itself fail or cancel" in text and "no implicit deadline" in text
    assert "its task stays `running`" not in text and "fails that task if" not in text
