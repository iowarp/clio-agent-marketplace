"""The case script's distance check does not trust a distance below the boxes' gap (FN-7)."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "pcb-enclosure" / "scripts" / "enclosure.py"


class _Box:
    def __init__(self, x0: float, y0: float, z0: float, x1: float, y1: float, z1: float) -> None:
        self.xmin, self.ymin, self.zmin, self.xmax, self.ymax, self.zmax = x0, y0, z0, x1, y1, z1


class _Shape:
    def __init__(self, box: _Box, reported: float) -> None:
        self._box, self._reported = box, reported

    def BoundingBox(self) -> _Box:  # noqa: N802 - CadQuery's name
        return self._box

    def distance(self, other: object) -> float:
        del other
        return self._reported


def _script() -> types.ModuleType:
    # The script imports CadQuery at the top; the gap helpers need none of it.
    sys.modules.setdefault("cadquery", types.ModuleType("cadquery"))
    module = sys.modules["cadquery"]
    if not hasattr(module, "Shape"):
        module.Shape = object  # type: ignore[attr-defined]
        module.Wire = object  # type: ignore[attr-defined]
    spec = importlib.util.spec_from_file_location("enclosure_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


class EnclosureGapTest(unittest.TestCase):
    def test_a_zero_distance_between_separated_boxes_is_replaced_by_their_gap(self) -> None:
        enclosure = _script()
        a = _Shape(_Box(0, 0, 0, 10, 10, 10), reported=0.0)
        b = _Shape(_Box(35, 0, 0, 40, 10, 10), reported=0.0)
        gap, method = enclosure._gap(a, b)
        self.assertAlmostEqual(gap, 25.0)
        self.assertIn("bounding boxes", method)

    def test_a_plausible_distance_is_kept(self) -> None:
        enclosure = _script()
        a = _Shape(_Box(0, 0, 0, 10, 10, 10), reported=26.5)
        b = _Shape(_Box(35, 0, 0, 40, 10, 10), reported=0.0)
        self.assertEqual(enclosure._gap(a, b), (26.5, "Shape.distance"))

    def test_overlapping_boxes_give_no_bound(self) -> None:
        enclosure = _script()
        a = _Shape(_Box(0, 0, 0, 10, 10, 10), reported=0.8)
        b = _Shape(_Box(5, 5, 5, 20, 20, 20), reported=0.0)
        self.assertEqual(enclosure._gap(a, b)[0], 0.8)


if __name__ == "__main__":
    unittest.main()
