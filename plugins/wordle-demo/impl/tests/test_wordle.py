"""wordle-demo: the shipped list is the generator's output; games are strict and secret."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from wordle_demo import wordgen
from wordle_demo.game import Bench, answer_set, feedback
from wordle_demo.server import CALLER_META_KEY, UI_EVENT_META_KEY, create_server

SECRET = "test-secret-not-the-real-one"
PLUGIN = Path(__file__).resolve().parents[2]


def test_the_shipped_list_is_the_versioned_generator_output() -> None:
    listed = wordgen.load()
    assert listed["version"] == wordgen.VERSION and listed["seed"] == wordgen.LIST_SEED
    assert listed["words"] == wordgen.generate()
    words = listed["words"]
    assert len(words) == wordgen.LIST_SIZE and all(len(w) == 5 and w.isalpha() for w in words)
    # Letter frequencies differ from English on purpose: 'e' is rare, 'u' and 'k' common.
    letters = "".join(words)
    assert letters.count("u") > 4 * letters.count("e")
    assert letters.count("k") > letters.count("s") + letters.count("t")


def test_feedback_follows_the_duplicate_letter_rule() -> None:
    assert feedback("kazuv", "kazuv") == ["correct"] * 5
    assert feedback("abuky", "yubak") == ["present"] * 5
    # One 'u' in the answer: only one of the two guessed 'u's is marked.
    assert feedback("kozuv", "uuzab") == ["present", "absent", "correct", "absent", "absent"]
    assert feedback("kuzuv", "uuzab") == ["present", "correct", "correct", "absent", "absent"]


def test_the_same_seed_gives_the_same_answer_and_the_secret_decides_it() -> None:
    one, two = Bench(SECRET), Bench(SECRET)
    assert one.new_game(7).answer == two.new_game(7).answer
    other = Bench(SECRET + "x")
    assert answer_set(SECRET, one.words) != answer_set(SECRET + "x", other.words)
    with pytest.raises(ValueError):
        Bench("")


async def test_guesses_are_strict_and_each_carries_its_board_event() -> None:
    server = create_server(SECRET)
    async with Client(server) as client:
        meta = {CALLER_META_KEY: {"session": "sess_branch", "root": "sess_root"}}
        call = await client.call_tool("new_game", {"seed": 3}, meta=meta)
        started = call.data
        game_id = started["game_id"]
        opened = call.meta[UI_EVENT_META_KEY]
        assert started["status"] == "playing" and opened["group"] == "sess_branch"
        assert opened["component"]["component"] == "BoardWall" and opened["rows"] == []
        assert "ui_event" not in json.dumps(started)  # the model never sees the event
        listed = (await client.call_tool("word_list", {})).data["words"]
        with pytest.raises(ToolError, match="wrong_length"):
            await client.call_tool("guess", {"game_id": game_id, "word": "abc"})
        with pytest.raises(ToolError, match="not_in_list"):
            await client.call_tool("guess", {"game_id": game_id, "word": "zzzzz"})
        state = (await client.call_tool("game_state", {"game_id": game_id})).data
        assert state["turns_used"] == 0  # rejected guesses cost no turn
        call = await client.call_tool("guess", {"game_id": game_id, "word": listed[0]})
        result = call.data
        assert len(result["feedback"]) == 5 and result["turns_left"] == 5
        event = call.meta[UI_EVENT_META_KEY]
        assert event["key"] == game_id and "component" not in event
        assert "".join(row["letter"] for row in event["rows"]).lower() == listed[0]
        assert [row["state"] for row in event["rows"]] == result["feedback"]
        # No result names the answer.
        answer = server_answer(server, game_id)
        for word in listed[1:6]:
            if word != answer:
                text = json.dumps(
                    (await client.call_tool("guess", {"game_id": game_id, "word": word})).data
                )
                assert answer not in text or answer == word


def server_answer(_server: object, game_id: str) -> str:
    """The answer, read from the bench object only to check results never carry it."""

    return _BENCHES[-1].game(game_id).answer


_BENCHES: list[Bench] = []
_original_init = Bench.__init__


def _tracking_init(self: Bench, *args: object, **kwargs: object) -> None:
    _original_init(self, *args, **kwargs)  # type: ignore[arg-type]
    _BENCHES.append(self)


Bench.__init__ = _tracking_init  # type: ignore[method-assign]


def test_hidden_material_is_in_no_plugin_file_and_no_workspace_file(tmp_path: Path) -> None:
    bench = Bench(SECRET)
    answers = answer_set(SECRET, bench.words)
    # The answer set as any file would hold it: a run of consecutive answers.
    probes = [" ".join(answers[i : i + 3]) for i in range(0, 30, 3)]
    probes += [json.dumps(answers[i : i + 3]) for i in range(0, 30, 3)]
    probes.append(SECRET)
    for path in [*PLUGIN.rglob("*"), *tmp_path.rglob("*")]:
        if not path.is_file() or ".venv" in path.parts or path.suffix in {".pyc"}:
            continue
        if path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not any(probe in text for probe in probes), path
