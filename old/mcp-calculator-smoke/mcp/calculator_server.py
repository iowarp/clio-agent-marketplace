#!/usr/bin/env python3
"""Minimal pack-local MCP server for CLIO marketplace execution tests."""

from __future__ import annotations

import json
import sys

from fastmcp import FastMCP

mcp = FastMCP("calculator-smoke")


@mcp.tool()
def calculator_add(a: float, b: float) -> dict[str, float]:
    """Add two numbers and return the operands plus the sum."""

    return {"a": a, "b": b, "sum": a + b}


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        mcp.run(transport="stdio", show_banner=False)
        return 0
    print(json.dumps({"name": "calculator-smoke", "tools": ["calculator_add"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
