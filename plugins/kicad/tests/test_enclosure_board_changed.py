"""The case is never built for a board that changed after it was measured (FQ7, FQ14).

Found live (FQ7): J1's 3D body was removed from the board file, and the case was built from
the STEP exported and measured before, which still held J1's body.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "pcb-enclosure" / "scripts"


class _Stub(types.ModuleType):
    """A module whose every attribute is a placeholder (these checks use none of them)."""

    def __getattr__(self, name: str) -> object:
        return object


def _load(name: str) -> types.ModuleType:
    # The scripts import CadQuery and OCP at the top; these checks run before any of it.
    for module in (
        "cadquery",
        "OCP",
        "OCP.STEPCAFControl",
        "OCP.TCollection",
        "OCP.TDataStd",
        "OCP.TDF",
        "OCP.TDocStd",
        "OCP.XCAFDoc",
    ):
        if module not in sys.modules or not isinstance(sys.modules[module], _Stub):
            sys.modules.setdefault(module, _Stub(module))
    spec = importlib.util.spec_from_file_location(f"{name}_under_test", SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded  # its dataclasses look their module up
    spec.loader.exec_module(loaded)
    return loaded


class BoardChangedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())
        self.step = self.dir / "board.step"
        self.pcb = self.dir / "board.kicad_pcb"
        self.step.write_text("ISO-10303-21;\n")
        self.pcb.write_text("(kicad_pcb (footprint J1))\n")

    def test_a_step_older_than_the_board_is_not_measured(self) -> None:
        envelope = _load("board_envelope")
        old = self.pcb.stat().st_mtime - 60
        os.utime(self.step, (old, old))
        with self.assertRaises(SystemExit) as stop:
            envelope.measure(self.step, self.pcb, "")
        self.assertIn("older than board.kicad_pcb", str(stop.exception))
        self.assertIn("Export the STEP again", str(stop.exception))

    def test_the_case_refuses_an_envelope_of_the_board_before_it_changed(self) -> None:
        enclosure = _load("enclosure")
        envelope = {
            "source": {
                "step": "board.step",
                "sha256": hashlib.sha256(self.step.read_bytes()).hexdigest(),
                "pcb": "board.kicad_pcb",
                "pcb_sha256": hashlib.sha256(self.pcb.read_bytes()).hexdigest(),
            },
            "missing_bodies": [],
        }
        (self.dir / "board-envelope.json").write_text(json.dumps(envelope))
        enclosure.HERE = self.dir
        enclosure.ENVELOPE = "board-envelope.json"
        self.pcb.write_text("(kicad_pcb)\n")  # J1 moved, or its body removed, in KiCad
        with self.assertRaises(SystemExit) as stop:
            enclosure._load_envelope()
        self.assertIn("changed after board-envelope.json was measured", str(stop.exception))


    def test_an_envelope_that_does_not_record_its_board_is_measured_again(self) -> None:
        enclosure = _load("enclosure")
        envelope = {
            "source": {
                "step": "board.step",
                "sha256": hashlib.sha256(self.step.read_bytes()).hexdigest(),
                "pcb": "board.kicad_pcb",
            },
            "missing_bodies": [],
        }
        (self.dir / "board-envelope.json").write_text(json.dumps(envelope))
        enclosure.HERE = self.dir
        enclosure.ENVELOPE = "board-envelope.json"
        with self.assertRaises(SystemExit) as stop:
            enclosure._load_envelope()
        self.assertIn("measure again", str(stop.exception))


    def test_a_body_the_board_file_no_longer_has_is_missing(self) -> None:
        """Found live (FQ7): J1's model was removed in the board file, and the STEP exported
        before still held its body, so the case was built around it."""
        envelope = _load("board_envelope")
        board = self.dir / "j1.kicad_pcb"
        board.write_text(
            '(kicad_pcb (footprint "USB_C" (layer "F.Cu") (at 4 22 -90)'
            ' (property "Reference" "J1"))'
            ' (footprint "R" (layer "F.Cu") (at 10 10) (property "Reference" "R1")'
            ' (model "R_0603.step")))'
        )
        footprints, _ = envelope.read_pcb(board)
        by_ref = {f.reference: f for f in footprints}
        in_the_old_step = {"J1": object(), "R1": object()}
        self.assertEqual(envelope.missing_bodies(by_ref, in_the_old_step), ["J1"])


if __name__ == "__main__":
    unittest.main()
