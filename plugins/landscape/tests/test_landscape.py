"""Flow routing on synthetic surfaces with known drainage, and the plugin's levels."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import numpy as np

PLUGIN = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "landscape_flow_routing", PLUGIN / "skills/terrain-from-lidar/scripts/flow_routing.py"
)
assert spec and spec.loader
flow = importlib.util.module_from_spec(spec)
sys.modules["landscape_flow_routing"] = flow
spec.loader.exec_module(flow)


def test_a_v_shaped_valley_drains_everything_to_one_outlet() -> None:
    rows, cols = 21, 15
    r, c = np.mgrid[0:rows, 0:cols]
    dem = np.abs(c - 7) * 2.0 + r * 0.5  # valley along column 7, falling toward row 0
    valid = np.ones(dem.shape, bool)
    result = flow.route(dem, valid, cell=10.0, stream_area_km2=0.002)
    area = result["area_km2"]
    # The outlet at the valley mouth collects (nearly) the whole grid.
    assert area[0, 7] >= 0.9 * rows * cols * 100 / 1e6
    assert result["streams"][:10, 7].all()  # headwater cells stay below the threshold
    assert not result["streams"][:, 0].any()


def test_a_pit_is_filled_and_still_drains() -> None:
    dem = np.full((9, 9), 10.0)
    dem[:, 0] = 5.0  # an outlet edge to the west
    dem[4, 4] = 1.0  # a closed depression
    result = flow.route(dem, np.ones(dem.shape, bool), cell=100.0, stream_area_km2=1.0)
    assert result["summary"]["filled_cells"] >= 1
    assert result["summary"]["largest_contributing_area_km2"] > 0


def test_nodata_cells_neither_send_nor_receive() -> None:
    dem = np.arange(25, dtype=float).reshape(5, 5)
    valid = np.ones(dem.shape, bool)
    valid[2, 2] = False
    result = flow.route(dem, valid, cell=1.0, stream_area_km2=1.0)
    assert result["area_km2"][2, 2] == 0


def test_skill_levels() -> None:
    for skill in (PLUGIN / "skills").glob("*/SKILL.md"):
        head = skill.read_text(encoding="utf-8").split("---", 2)[1]
        assert re.findall(r"(?m)^- level:(L[0-3])$", head) == ["L1"], skill
