"""Typed refusals: every failed call names its reason first, then says what to do."""

from __future__ import annotations

from typing import NoReturn

from fastmcp.exceptions import ToolError


def refuse(reason: str, message: str) -> NoReturn:
    """Raise a tool error the model and a script both read as ``reason: message``."""
    raise ToolError(f"{reason}: {message}")
