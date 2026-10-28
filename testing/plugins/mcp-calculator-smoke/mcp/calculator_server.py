#!/usr/bin/env python3
"""Minimal plugin-local MCP server for CLIO marketplace execution tests.

Declared as server ``calculator`` in the plugin's ``mcp.json``, so its ``add`` tool
reaches the agent as ``calculator_add``.
"""

from __future__ import annotations

import json
import sys

from fastmcp import FastMCP

mcp = FastMCP("calculator-smoke")


@mcp.tool()
def add(a: float, b: float) -> dict[str, float]:
    """Add two numbers and return the operands plus the sum."""

    return {"a": a, "b": b, "sum": a + b}


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        mcp.run(transport="stdio", show_banner=False)
        return 0
    print(json.dumps({"name": "calculator-smoke", "tools": ["add"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
