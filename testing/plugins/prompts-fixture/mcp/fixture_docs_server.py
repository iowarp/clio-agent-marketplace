#!/usr/bin/env python3
"""The prompts-fixture MCP server: two prompts and three tools, for CLIO's tests.

Prompts: ``define_term`` (one required argument) and ``show_figure`` (returns text, an
embedded resource and an image). Tools: ``lookup_term``, ``count_words`` and
``list_notes``. With ``serve --extra-prompt`` it adds a third prompt a minute after
starting and tells its clients, for the prompt-list-changed test.
"""

from __future__ import annotations

import base64
import json
import sys

from fastmcp import FastMCP
from fastmcp.prompts import Message
from mcp.types import EmbeddedResource, ImageContent, TextResourceContents

mcp = FastMCP("fixture-docs")

GLOSSARY = {
    "burst buffer": "A fast storage tier that absorbs I/O bursts before draining them to the parallel file system.",
    "checkpoint": "A saved copy of a running job's state, written so the job can restart after a failure.",
}

# A 2x2 red PNG.
_PNG = base64.b64encode(
    bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000020000000208020000"
        "00fdd49a730000001549444154789c63f8cfc0f09f81e13f03c3ff0c"
        "0c0c00f40f03fd1b0e4f6e0000000049454e44ae426082"
    )
).decode()


@mcp.prompt()
def define_term(term: str) -> str:
    """Define one glossary term for the person, with an example."""
    return f"Define the term '{term}' using the fixture glossary, then give one example of it in use."


@mcp.prompt()
def show_figure(caption: str = "Fixture figure") -> list[Message]:
    """Show the fixture figure with its caption and the data note it comes from."""
    return [
        Message(f"Describe this figure in one sentence. Its caption is: {caption}"),
        Message(
            EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri="fixture://notes/figure-data",
                    mimeType="text/plain",
                    text="figure-data: two red pixels, drawn by the fixture server",
                ),
            )
        ),
        Message(ImageContent(type="image", data=_PNG, mimeType="image/png")),
        Message("The figure is a fixture; do not look for it in the workspace.", role="assistant"),
    ]


@mcp.tool()
def lookup_term(term: str) -> dict[str, str]:
    """Look one term up in the fixture glossary."""
    return {"term": term, "definition": GLOSSARY.get(term.lower(), "not in the glossary")}


@mcp.tool()
def count_words(text: str) -> dict[str, int]:
    """Count the words in a text."""
    return {"words": len(text.split())}


@mcp.tool()
def list_notes() -> dict[str, list[str]]:
    """List the fixture's notes."""
    return {"notes": ["figure-data", "glossary"]}


def _add_extra_prompt_later() -> None:
    import threading  # noqa: PLC0415

    def add() -> None:
        @mcp.prompt()
        def summarize_notes() -> str:
            """Summarize the fixture's notes (added while the server runs)."""
            return "Summarize the fixture notes: figure-data and glossary."

    threading.Timer(60.0, add).start()


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        if "--extra-prompt" in sys.argv:
            _add_extra_prompt_later()
        mcp.run(transport="stdio", show_banner=False)
        return 0
    print(json.dumps({"name": "fixture-docs", "prompts": ["define_term", "show_figure"], "tools": ["lookup_term", "count_words", "list_notes"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
