"""The wordle-demo MCP server: ``word_list``, ``new_game``, ``guess``, ``game_state``.

Every ``new_game`` and ``guess`` result carries a board record in its result
``_meta`` (``ai.iowarp.clio/ui_event``), which CLIO keeps and never shows the model:
the game's tiles so far, keyed by game and grouped by the calling branch (CLIO stamps
the calling session in each call's ``_meta`` as ``ai.iowarp.clio/caller``), so games
are recorded as they are played without the agent narrating them. A study reads them as ``study://<study>/records/board``, and its
agent decides whether and how a view draws them.
"""

from __future__ import annotations

import json
import os
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult
from mcp.types import TextContent

from wordle_demo.game import Bench, Game, GuessRejected

CALLER_META_KEY = "ai.iowarp.clio/caller"
UI_EVENT_META_KEY = "ai.iowarp.clio/ui_event"
VIEW = "board"


def caller(ctx: Context | None) -> dict[str, str]:
    """``{"session", "root"}`` of the calling CLIO session, or ``{}``."""

    try:
        meta = ctx.request_context.meta if ctx is not None else None  # type: ignore[union-attr]
    except (AttributeError, LookupError, ValueError):
        return {}
    if meta is None:
        return {}
    data = meta.model_dump(by_alias=True) if hasattr(meta, "model_dump") else dict(meta)
    value = data.get(CALLER_META_KEY) or {}
    return {k: str(v) for k, v in value.items()} if isinstance(value, dict) else {}


def board_event(game: Game) -> dict[str, Any]:
    """The board record of ``game``: all of its tiles so far (the latest event wins)."""

    rows = [
        {
            "game": game.id,
            "board": f"{game.branch[-6:]} {game.id}",
            "turn": turn,
            "pos": pos,
            "letter": letter.upper(),
            "state": mark,
            "word": word,
            "status": game.status,
            "turns": len(game.guesses),
        }
        for turn, (word, marks) in enumerate(zip(game.guesses, game.marks, strict=True), 1)
        for pos, (letter, mark) in enumerate(zip(word, marks, strict=True))
    ]
    return {"view": VIEW, "key": game.id, "group": game.branch, "rows": rows}


def _result(payload: dict[str, Any], event: dict[str, Any]) -> ToolResult:
    """The model sees ``payload``; the board record rides in the result ``_meta``."""

    return ToolResult(
        content=[TextContent(type="text", text=json.dumps(payload))],
        structured_content=payload,
        meta={UI_EVENT_META_KEY: event},
    )


def create_server(secret: str | None = None) -> FastMCP:
    bench = Bench(secret if secret is not None else os.environ.get("WORDLE_SECRET_SEED", ""))
    mcp = FastMCP("wordle")

    def rejected(error: GuessRejected) -> ToolError:
        return ToolError(f"{error.reason}: {error}")

    @mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
    def word_list() -> dict[str, Any]:
        """Every valid guess (five-letter words). Answers come from this list; which
        words are answers is hidden."""

        return {"version": bench.version, "count": len(bench.words), "words": bench.words}

    @mcp.tool
    def new_game(seed: int, ctx: Context) -> ToolResult:
        """Start a game. The same seed always gives the same answer. Returns its id."""

        who = caller(ctx)
        game = bench.new_game(seed, who.get("session", ""), who.get("root", ""))
        return _result(game.state(), board_event(game))

    @mcp.tool
    def guess(game_id: str, word: str) -> ToolResult:
        """Guess a word in a game: per-letter feedback (correct, present, absent) and
        turns left. A wrong-length or unknown word is an error that costs no turn."""

        try:
            game = bench.guess(game_id, word)
        except GuessRejected as error:
            raise rejected(error) from error
        marks = game.marks[-1]
        payload = {
            "game_id": game.id,
            "word": game.guesses[-1],
            "feedback": marks,
            "pattern": "".join({"correct": "G", "present": "Y"}.get(m, "-") for m in marks),
            "turns_used": len(game.guesses),
            "turns_left": 6 - len(game.guesses),
            "status": game.status,
        }
        return _result(payload, board_event(game))

    @mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
    def game_state(game_id: str) -> dict[str, Any]:
        """A game's guesses, feedback and status (solved, failed or playing)."""

        try:
            return bench.game(game_id).state()
        except GuessRejected as error:
            raise rejected(error) from error

    return mcp


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()
