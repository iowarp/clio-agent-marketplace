"""Typed errors exposed by the Spotter provenance MCP."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from fastmcp.exceptions import ToolError


@dataclass
class ProvenanceError(RuntimeError):
    """A safe provider/query failure with a stable public code."""

    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message

    def as_tool_error(self) -> ToolError:
        """Convert this failure into an MCP-visible structured tool error."""
        return ToolError(
            json.dumps(
                {"code": self.code, "message": self.message, "details": self.details},
                separators=(",", ":"),
            )
        )


def capability_unavailable(tool: str, provider: str) -> ProvenanceError:
    """Build an unsupported-capability error without semantic fallback."""
    return ProvenanceError(
        code="capability_unavailable",
        message=f"{provider} cannot answer {tool}",
        details={"tool": tool, "provider": provider},
    )
