"""The wordle-demo MCP server: ``word_list``, ``new_game``, ``guess``, ``game_state``.

Every ``new_game`` and ``guess`` result carries a board-wall event in its result
``_meta`` (``ai.iowarp.clio/ui_event``), which CLIO records for the UI and never shows
the model: the game's tiles so far, keyed by game and grouped by the calling branch
(CLIO stamps the calling session in each call's ``_meta`` as
``ai.iowarp.clio/caller``). Games appear on the wall as they are played without the
agent narrating them. A game's first event also carries the wall's chart component,
the ``BoardWall`` of this plugin's ``wordle-board`` catalog.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult
from mcp.types import TextContent

from wordle_demo.game import Bench, Game, GuessRejected

CALLER_META_KEY = "ai.iowarp.clio/caller"
UI_EVENT_META_KEY = "ai.iowarp.clio/ui_event"
CATALOG_ID = "https://iowarp.ai/a2ui/catalogs/wordle-board/v1"
VIEW = "wordle-board/wall"
_ROOT = Path(os.environ.get("PLUGIN_ROOT") or Path(__file__).resolve().parents[3])
_SPEC = _ROOT / "ai.iowarp.clio" / "a2ui" / "wordle-board"


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


def wall_component() -> dict[str, Any]:
    """The wall's A2UI component: ``BoardWall`` (the chart kernel with the board spec)."""

    spec = json.loads((_SPEC / "board_spec.json").read_text(encoding="utf-8"))
    return {"id": "wall", "component": "BoardWall", "spec": spec, "title": "Board wall"}


def board_event(game: Game, *, with_component: bool = False) -> dict[str, Any]:
    """The wall's event for ``game``: all of its tiles so far (the latest event wins)."""

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
    event: dict[str, Any] = {
        "view": VIEW,
        "catalog": CATALOG_ID,
        "key": game.id,
        "group": game.branch,
        "rows": rows,
    }
    if with_component:
        event["component"] = wall_component()
    return event


def _result(payload: dict[str, Any], event: dict[str, Any]) -> ToolResult:
    """The model sees ``payload``; the wall's event rides in the result ``_meta``."""

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
        return _result(game.state(), board_event(game, with_component=True))

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
