"""hidden-law-bench: a secret-seeded law with the family's four properties; strict tools."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from hidden_law_bench.law import INPUTS, NOISE_S, draw_law, held_out_settings, textbook_period
from hidden_law_bench.server import CALLER_META_KEY, UI_EVENT_META_KEY, create_server

SECRET = "test-secret-not-the-real-one"
PLUGIN = Path(__file__).resolve().parents[2]
MID = {name: (low + high) / 2 for name, (_u, low, high, _r) in INPUTS.items()}


@pytest.mark.parametrize("secret", [SECRET, "another", "a third secret"])
def test_every_drawn_law_has_the_familys_four_properties(secret: str) -> None:
    law = draw_law(secret)
    assert 0.56 <= law.length_exponent <= 0.68  # not the textbook 0.5
    assert {law.second, law.regime, law.decoy} == {
        "bob_mass_kg",
        "release_angle_deg",
        "ambient_temp_c",
    }
    base = dict(MID, **{law.regime: INPUTS[law.regime][1]})
    # The decoy has no effect at all.
    _u, low, high, _r = INPUTS[law.decoy]
    assert law.period({**base, law.decoy: low}) == law.period({**base, law.decoy: high})
    # The second input has an effect.
    _u, low, high, _r = INPUTS[law.second]
    assert law.period({**base, law.second: low}) != law.period({**base, law.second: high})
    # Below the threshold the regime input does nothing; above it, it does.
    _u, low, high, _r = INPUTS[law.regime]
    below = law.period({**base, law.regime: low})
    assert below == law.period({**base, law.regime: law.threshold * 0.999})
    assert law.period({**base, law.regime: high}) > below * 1.05
    # A recalled textbook law is measurably wrong across the held-out settings.
    errors = [
        abs(10 * (law.period(s) - textbook_period(s))) / NOISE_S
        for s in held_out_settings(secret)
    ]
    assert sum(errors) / len(errors) > 3


async def test_measurements_are_strict_kept_per_study_and_carry_their_event() -> None:
    server = create_server(SECRET)
    one = {CALLER_META_KEY: {"session": "sess_a", "root": "sess_study1"}}
    two = {CALLER_META_KEY: {"session": "sess_b", "root": "sess_study2"}}
    async with Client(server) as client:
        described = (await client.call_tool("apparatus", {})).data
        assert set(described["inputs"]) == set(INPUTS) and described["noise"]
        for bad, reason in (
            ({**MID, "arm_length_m": 9.0}, "out_of_range"),
            ({"arm_length_m": 1.0}, "settings_invalid"),
            ({**MID, "colour": 1}, "settings_invalid"),
        ):
            with pytest.raises(ToolError, match=reason):
                await client.call_tool("measure", {"settings": bad}, meta=one)
        first = await client.call_tool("measure", {"settings": MID, "repeats": 3}, meta=one)
        readings = first.data["readings"]
        assert len(readings) == 3 and len({r["ten_cycles_s"] for r in readings}) == 3
        event = first.meta[UI_EVENT_META_KEY]
        assert event["group"] == "sess_a" and event["component"]["component"] == "Readings"
        assert len(event["rows"]) == 3 and "branch" not in json.dumps(first.data)
        again = await client.call_tool("measure", {"settings": MID}, meta=one)
        assert "component" not in again.meta[UI_EVENT_META_KEY]
        await client.call_tool("measure", {"settings": MID}, meta=two)
        history = (await client.call_tool("history", {}, meta=one)).data
        assert history["count"] == 4 and list(history["branches"]) == ["sess_a"]


def test_the_law_is_in_no_plugin_file_and_no_workspace_file(tmp_path: Path) -> None:
    facts = draw_law(SECRET).facts()
    probes = [SECRET] + [
        repr(value) for value in facts.values() if isinstance(value, float)
    ]
    for path in [*PLUGIN.rglob("*"), *tmp_path.rglob("*")]:
        if not path.is_file() or ".venv" in path.parts or path.suffix == ".pyc":
            continue
        if path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not any(probe in text for probe in probes), path
