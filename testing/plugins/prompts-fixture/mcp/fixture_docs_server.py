#!/usr/bin/env python3
"""The prompts-fixture MCP server: two prompts and three tools, for CLIO's tests.

Prompts: ``define_term`` (one required argument) and ``show_figure`` (returns text, an
embedded resource, an image and an assistant message). Tools: ``lookup_term``,
``count_words``, ``list_notes`` and ``publish_summary_prompt``, which publishes a third
prompt (the prompt-list-changed test).

Publishing leaves a marker in the plugin's data folder and announces
``notifications/prompts/list_changed`` in the call's own reply. Every running copy of
the server watches for the marker and adds ``summarize_notes``, so a client that calls
tools on one connection and lists prompts on another sees the new prompt on both.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastmcp import Context, FastMCP
from fastmcp.prompts import Message
from mcp.types import EmbeddedResource, ImageContent, TextResourceContents

MARKER = Path(os.environ.get("PLUGIN_DATA") or ".") / "summary-prompt-published"


def _summarize_notes() -> str:
    """Summarize the fixture's notes (published while the server runs)."""
    return "Summarize the fixture notes: figure-data and glossary."


_published = False


def _publish_here() -> None:
    global _published
    if not _published:
        mcp.prompt(name="summarize_notes")(_summarize_notes)
        _published = True


async def _watch_marker() -> None:
    while not MARKER.exists():
        await asyncio.sleep(0.5)
    _publish_here()


@asynccontextmanager
async def _lifespan(_server):
    watcher = asyncio.create_task(_watch_marker())
    try:
        yield {}
    finally:
        watcher.cancel()


mcp = FastMCP("fixture-docs", lifespan=_lifespan)

GLOSSARY = {
    "burst buffer": "A fast storage tier that absorbs I/O bursts before draining them to the parallel file system.",
    "checkpoint": "A saved copy of a running job's state, written so the job can restart after a failure.",
}

# A 2x2 red PNG.
_PNG = base64.b64encode(
    bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000020000000208020000"
        "00fdd49a730000001049444154789c63f8cfc000440c100a001fee03"
        "fd8b5f14d40000000049454e44ae426082"
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
        Message(
            "The figure is a fixture; do not look for it in the workspace.",
            role="assistant",
        ),
    ]


@mcp.tool()
def lookup_term(term: str) -> dict[str, str]:
    """Look one term up in the fixture glossary."""
    return {
        "term": term,
        "definition": GLOSSARY.get(term.lower(), "not in the glossary"),
    }


@mcp.tool()
def count_words(text: str) -> dict[str, int]:
    """Count the words in a text."""
    return {"words": len(text.split())}


@mcp.tool()
def list_notes() -> dict[str, list[str]]:
    """List the fixture's notes."""
    return {"notes": ["figure-data", "glossary"]}


@mcp.tool()
async def publish_summary_prompt(ctx: Context) -> str:
    """Publish the summarize_notes prompt and tell the client the prompt list changed."""

    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text("published\n", encoding="utf-8")
    _publish_here()
    # fastmcp announces a visibility change in this reply (prompts/list_changed among them).
    await ctx.enable_components(names={"summarize_notes"})
    return "summarize_notes is published; the client was told the prompt list changed"


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        mcp.run(transport="stdio", show_banner=False)
        return 0
    print(
        json.dumps(
            {
                "name": "fixture-docs",
                "prompts": ["define_term", "show_figure"],
                "tools": [
                    "lookup_term",
                    "count_words",
                    "list_notes",
                    "publish_summary_prompt",
                ],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
