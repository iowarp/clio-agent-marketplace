"""The apparatus and its hidden law, drawn from a secret seed.

The law is generated rather than taken from physics, so a recited textbook answer is
measurably wrong. One law is drawn per secret seed (``BENCH_SECRET_SEED`` in the
server's environment) from a family with four properties:

* the period depends on arm length through a non-textbook exponent (0.56 to 0.68,
  not 0.5), and on a second input through a weak power;
* one input has no effect at all;
* one input changes the regime above a threshold: below it the law is a pure power
  law, above it a further power of (input / threshold) multiplies it;
* each reading (the time for ten cycles) carries Gaussian noise at the stated level.

Which of bob mass, release angle and ambient temperature plays which role is drawn
from the seed too. The law is never written to a file or returned by a tool.
"""

from __future__ import annotations

import hashlib
import hmac
import math
import random
from dataclasses import dataclass
from typing import Any

#: The controllable inputs: name -> (unit, low, high, reference value).
INPUTS: dict[str, tuple[str, float, float, float]] = {
    "arm_length_m": ("m", 0.2, 2.0, 1.0),
    "bob_mass_kg": ("kg", 0.05, 2.0, 0.5),
    "release_angle_deg": ("deg", 2.0, 80.0, 20.0),
    "ambient_temp_c": ("degC", -10.0, 40.0, 20.0),
}
CYCLES = 10
#: Standard deviation of one reading of the time for ten cycles, in seconds.
NOISE_S = 0.05
_ROLE_INPUTS = ("bob_mass_kg", "release_angle_deg", "ambient_temp_c")


def digest(secret: str, label: str) -> int:
    mac = hmac.new(secret.encode(), label.encode(), hashlib.sha256).digest()
    return int.from_bytes(mac[:8], "big")


def _scaled(name: str, value: float) -> float:
    """An input relative to its reference (temperatures in kelvin)."""

    reference = INPUTS[name][3]
    if name == "ambient_temp_c":
        return (value + 273.15) / (reference + 273.15)
    return value / reference


@dataclass(frozen=True)
class Law:
    scale_s: float
    length_exponent: float
    second: str
    second_exponent: float
    regime: str
    threshold: float
    regime_exponent: float
    decoy: str

    def period(self, settings: dict[str, float]) -> float:
        """Seconds per cycle at ``settings`` (noise-free)."""

        value = self.scale_s * settings["arm_length_m"] ** self.length_exponent
        value *= _scaled(self.second, settings[self.second]) ** self.second_exponent
        above = settings[self.regime]
        if above > self.threshold:
            value *= (above / self.threshold) ** self.regime_exponent
        return value

    def facts(self) -> dict[str, Any]:
        """The law's parameters, for the offline scorer only."""

        return {
            "scale_s": self.scale_s,
            "length_exponent": self.length_exponent,
            "second": self.second,
            "second_exponent": self.second_exponent,
            "regime": self.regime,
            "threshold": self.threshold,
            "regime_exponent": self.regime_exponent,
            "decoy": self.decoy,
        }


def draw_law(secret: str) -> Law:
    """The law for ``secret``."""

    if not secret:
        raise ValueError("BENCH_SECRET_SEED is not set: the bench needs the secret seed")
    rng = random.Random(digest(secret, "law"))
    second, regime, decoy = rng.sample(_ROLE_INPUTS, 3)
    _unit, low, high, _ref = INPUTS[regime]
    if regime == "ambient_temp_c":
        # A threshold on a temperature that can be negative: keep it positive.
        threshold = rng.uniform(15.0, 30.0)
    else:
        threshold = rng.uniform(low + 0.35 * (high - low), low + 0.65 * (high - low))
    return Law(
        scale_s=rng.uniform(1.8, 2.3),
        length_exponent=rng.uniform(0.56, 0.68),
        second=second,
        second_exponent=rng.choice((-1, 1)) * rng.uniform(0.06, 0.14),
        regime=regime,
        threshold=threshold,
        regime_exponent=rng.uniform(0.25, 0.45),
        decoy=decoy,
    )


def held_out_settings(secret: str, count: int = 50) -> list[dict[str, float]]:
    """Settings the agent never measured, across the full range, regime included."""

    rng = random.Random(digest(secret, "held-out"))
    rows = []
    for _ in range(count):
        rows.append(
            {name: rng.uniform(low, high) for name, (_u, low, high, _r) in INPUTS.items()}
        )
    return rows


def textbook_period(settings: dict[str, float]) -> float:
    """The small-angle pendulum law a recalled answer would give: 2 pi sqrt(L / g)."""

    return 2 * math.pi * math.sqrt(settings["arm_length_m"] / 9.81)
