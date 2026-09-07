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


def test_model_instructions_do_not_reference_removed_or_bounded_task_collection() -> (
    None
):
    violations: list[str] = []
    for path in _model_instruction_files():
        text = path.read_text(encoding="utf-8")
        if "check_agent_tasks" in text:
            violations.append(f"{path.relative_to(ROOT)} references check_agent_tasks")
        if re.search(r"wait_agent_tasks[^\n]{0,120}timeout_s", text):
            violations.append(
                f"{path.relative_to(ROOT)} gives wait_agent_tasks a timeout"
            )

    assert violations == []
