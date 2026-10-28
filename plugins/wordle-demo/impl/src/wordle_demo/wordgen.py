"""The word list: pronounceable five-letter pseudo-words, generated and versioned.

The list is generated, not taken from English, so recalled Wordle knowledge does not
help: its letter frequencies deliberately differ from English (``k``, ``z``, ``v``,
``u`` and ``y`` are common; ``e``, ``s`` and ``t`` are rare). The generator is seeded
and versioned; the shipped ``data/words-v<version>.json`` is its output, and a test
regenerates it. Which words are answers is not in the list: answers are drawn from a
secret seed at server start (:mod:`wordle_demo.game`).
"""

from __future__ import annotations

import json
import random
from pathlib import Path

VERSION = "1"
#: The public generator seed of list version 1 (the list is public; answers are not).
LIST_SEED = 20261027
LIST_SIZE = 3000

# Weighted inventories: weight per letter, skewed away from English frequencies.
_CONSONANTS = {
    "k": 9, "z": 7, "v": 7, "r": 6, "m": 6, "n": 6, "d": 5, "g": 5, "b": 5, "l": 5,
    "p": 4, "f": 4, "h": 3, "j": 3, "w": 3, "x": 2, "c": 2, "q": 1, "s": 1, "t": 1,
}  # fmt: skip
_VOWELS = {"u": 9, "a": 8, "o": 7, "i": 6, "y": 5, "e": 2}
#: Syllable shapes for five letters (C consonant, V vowel).
_SHAPES = ("CVCVC", "CVCCV", "VCVCV", "CVVCV", "CCVCV", "VCCVC")


def _pick(rng: random.Random, weights: dict[str, int]) -> str:
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def generate(seed: int = LIST_SEED, size: int = LIST_SIZE) -> list[str]:
    """``size`` distinct pronounceable five-letter pseudo-words, sorted."""

    rng = random.Random(seed)
    words: set[str] = set()
    while len(words) < size:
        shape = rng.choice(_SHAPES)
        word = "".join(_pick(rng, _VOWELS if slot == "V" else _CONSONANTS) for slot in shape)
        # No letter three times: keeps the words pronounceable and the feedback varied.
        if max(word.count(letter) for letter in word) < 3:
            words.add(word)
    return sorted(words)


def data_path(version: str = VERSION) -> Path:
    return Path(__file__).with_name("data") / f"words-v{version}.json"


def load(version: str = VERSION) -> dict[str, object]:
    """The shipped list: ``{"version", "seed", "size", "words"}``."""

    return json.loads(data_path(version).read_text(encoding="utf-8"))


def write(version: str = VERSION) -> Path:
    """Regenerate the shipped list file (run when a new version is cut)."""

    path = data_path(version)
    payload = {"version": version, "seed": LIST_SEED, "size": LIST_SIZE, "words": generate()}
    path.write_text(json.dumps(payload, indent=0) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    print(write())
