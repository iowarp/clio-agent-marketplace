"""Games: answers drawn from a secret seed, strict guesses, per-letter feedback.

The answer subset and each game's answer are derived at server start from the secret
seed in the server's environment (``WORDLE_SECRET_SEED``). They are never written to a
file, returned by a tool, or put in an error: a tool result carries only feedback.
The same game seed always gives the same answer, so a study's games can be replayed
offline by whoever holds the secret.
"""

from __future__ import annotations

import hashlib
import hmac
import random
from dataclasses import dataclass, field
from typing import Any

from wordle_demo import wordgen

MAX_TURNS = 6
#: The share of the list that can be an answer.
ANSWER_SHARE = 0.25
CORRECT, PRESENT, ABSENT = "correct", "present", "absent"


class GuessRejected(ValueError):
    """A guess that costs no turn: wrong length, not in the list, or a finished game."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


def _digest(secret: str, label: str) -> int:
    mac = hmac.new(secret.encode(), label.encode(), hashlib.sha256).digest()
    return int.from_bytes(mac[:8], "big")


def answer_set(secret: str, words: list[str]) -> list[str]:
    """The hidden answer subset of ``words`` for ``secret``."""

    rng = random.Random(_digest(secret, "answers"))
    return sorted(rng.sample(words, round(len(words) * ANSWER_SHARE)))


def feedback(answer: str, guess: str) -> list[str]:
    """Per-letter feedback with Wordle's duplicate-letter rule."""

    result = [ABSENT] * len(guess)
    remaining: dict[str, int] = {}
    for index, (want, got) in enumerate(zip(answer, guess, strict=True)):
        if want == got:
            result[index] = CORRECT
        else:
            remaining[want] = remaining.get(want, 0) + 1
    for index, got in enumerate(guess):
        if result[index] != CORRECT and remaining.get(got, 0) > 0:
            result[index] = PRESENT
            remaining[got] -= 1
    return result


@dataclass
class Game:
    id: str
    seed: int
    branch: str
    study: str
    answer: str = field(repr=False)
    guesses: list[str] = field(default_factory=list)
    marks: list[list[str]] = field(default_factory=list)

    @property
    def solved(self) -> bool:
        return bool(self.marks) and all(mark == CORRECT for mark in self.marks[-1])

    @property
    def status(self) -> str:
        if self.solved:
            return "solved"
        return "failed" if len(self.guesses) >= MAX_TURNS else "playing"

    def state(self) -> dict[str, Any]:
        """What a player may know: guesses, feedback and status, never the answer."""

        return {
            "game_id": self.id,
            "seed": self.seed,
            "guesses": [
                {"word": word, "feedback": marks}
                for word, marks in zip(self.guesses, self.marks, strict=True)
            ],
            "turns_used": len(self.guesses),
            "turns_left": MAX_TURNS - len(self.guesses),
            "status": self.status,
        }


class Bench:
    """Every game of this server process, keyed by id."""

    def __init__(self, secret: str, version: str = wordgen.VERSION) -> None:
        if not secret:
            raise ValueError("WORDLE_SECRET_SEED is not set: games need the secret seed")
        listed = wordgen.load(version)
        self.version = str(listed["version"])
        self.words: list[str] = list(listed["words"])  # type: ignore[arg-type]
        self._known = set(self.words)
        self._secret = secret
        self._answers = answer_set(secret, self.words)
        self.games: dict[str, Game] = {}

    def new_game(self, seed: int, branch: str = "", study: str = "") -> Game:
        answer = self._answers[_digest(self._secret, f"game:{int(seed)}") % len(self._answers)]
        number = len(self.games) + 1
        game = Game(f"g{number}-s{int(seed)}", int(seed), branch, study, answer)
        self.games[game.id] = game
        return game

    def game(self, game_id: str) -> Game:
        game = self.games.get(str(game_id))
        if game is None:
            raise GuessRejected("game_unknown", f"no game {game_id!r}; start one with new_game")
        return game

    def guess(self, game_id: str, word: str) -> Game:
        game = self.game(game_id)
        word = str(word or "").strip().lower()
        if game.status != "playing":
            raise GuessRejected("game_over", f"game {game_id} is {game.status}")
        if len(word) != 5:
            raise GuessRejected("wrong_length", f"{word!r} is not five letters; no turn used")
        if word not in self._known:
            raise GuessRejected("not_in_list", f"{word!r} is not in the word list; no turn used")
        game.guesses.append(word)
        game.marks.append(feedback(game.answer, word))
        return game
