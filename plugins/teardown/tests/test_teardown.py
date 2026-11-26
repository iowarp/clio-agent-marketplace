"""The teardown plugin's geometry, page and helpers do what its skills promise."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

PLUGIN = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN / "skills" / "exploded-teardown" / "scripts"
sys.path.insert(0, str(SCRIPTS))

geo = importlib.import_module("teardown_geometry")
build_teardown = importlib.import_module("build_teardown")
find_chromium = importlib.import_module("find_chromium")


def _first_group(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.S)
    assert match is not None, pattern
    return match.group(1)


def _doc_example() -> dict:
    text = (PLUGIN / "skills" / "exploded-teardown" / "references" / "spec.md").read_text(encoding="utf-8")
    block = text.split("## A small complete example", 1)[1]
    return json.loads(_first_group(r"```json\n(.*?)```", block))


def _assembly(spec: dict) -> Any:
    return geo.build_assembly(spec, PLUGIN)


class SpecTests(unittest.TestCase):
    def test_documented_example_builds_with_no_overlap_when_exploded(self) -> None:
        assembly = _assembly(_doc_example())
        self.assertEqual(geo.overlaps(assembly, 1.0), [])
        self.assertEqual([p.id for p in assembly.parts if p.id.startswith("bolt")], [f"bolt-{i}" for i in range(1, 7)])
        self.assertEqual(assembly.notes, [])

    def test_stages_come_away_one_after_another(self) -> None:
        assembly = _assembly(_doc_example())
        lid = next(p for p in assembly.parts if p.id == "lid")
        pinion = next(p for p in assembly.parts if p.id == "pinion")
        self.assertAlmostEqual(assembly.explode_offset(lid, 0.5)[2], lid.explode_distance)
        self.assertEqual(assembly.explode_offset(pinion, 0.5), (0.0, 0.0, 0.0))

    def test_repeated_copies_run_out_of_phase_by_input_step(self) -> None:
        spec = {
            "title": "t",
            "input": {"min": 0, "max": 360},
            "parts": [
                {
                    "id": "cam",
                    "note": "n",
                    "shape": {"type": "cylinder", "radius": 1, "height": 1},
                    "repeat": {"count": 2, "offset": [10, 0, 0], "input_step": 90},
                    "motion": {"type": "rotate", "ratio": 2},
                },
            ],
        }
        first, second = _assembly(spec).parts
        self.assertAlmostEqual(first.motion.angle[0], 0.0)
        self.assertAlmostEqual(second.motion.angle[0], 180.0)
        self.assertAlmostEqual(second.pivot[0], 10.0)

    def test_motion_without_an_input_and_unknown_focus_are_refused(self) -> None:
        part = {"id": "a", "shape": {"type": "box", "size": [1, 1, 1]}}
        with self.assertRaisesRegex(geo.SpecError, "top-level 'input'"):
            _assembly({"title": "t", "parts": [{**part, "motion": {"type": "rotate"}}]})
        with self.assertRaisesRegex(geo.SpecError, "unknown parts"):
            _assembly({"title": "t", "parts": [part], "steps": [{"title": "s", "focus": ["nope"]}]})


class PageTests(unittest.TestCase):
    def test_page_inlines_three_its_licence_and_the_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp)
            (pkg / "package.json").write_text(json.dumps({"name": "three", "version": "0.0.0-test"}), encoding="utf-8")
            for key, rel in build_teardown.THREE_FILES.items():
                (pkg / rel).parent.mkdir(parents=True, exist_ok=True)
                (pkg / rel).write_text("THREE LICENSE TEXT" if key == "license" else f"/* {key} */", encoding="utf-8")
            page = build_teardown.build_html(_assembly(_doc_example()), build_teardown.three_sources(str(pkg), None))
        self.assertIn("THREE LICENSE TEXT", page)
        self.assertIn('id="td-mesh"', page)
        self.assertNotRegex(page, r'<script[^>]+src="https?:')
        meta = json.loads(_first_group(r'id="td-meta">(.*?)</script>', page).replace("<\\/", "</"))
        self.assertEqual(meta["title"], "Spur gear reducer")


class ProvenanceAndHelperTests(unittest.TestCase):
    def test_upstream_licence_is_verbatim(self) -> None:
        recorded = json.loads((PLUGIN / "upstream.json").read_text(encoding="utf-8"))["files"]["LICENSE"]
        licence = (PLUGIN / "LICENSE.upstream").read_bytes().replace(b"\r\n", b"\n")  # autocrlf checkouts
        self.assertEqual(hashlib.sha256(licence).hexdigest(), recorded)

    def test_find_chromium_takes_the_newest_complete_build_in_clio_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            exe = "chrome.exe" if sys.platform == "win32" else "chrome"
            for release, build, complete in (("1.9.0", "1", True), ("1.10.0", "2", True), ("1.11.0", "3", False)):
                folder = Path(tmp) / "browser" / f"playwright-{release}" / f"chromium-{build}"
                (folder / "chrome-dir").mkdir(parents=True)
                (folder / "chrome-dir" / exe).write_bytes(b"")
                os.chmod(folder / "chrome-dir" / exe, 0o755)
                if complete:
                    (folder / "INSTALLATION_COMPLETE").write_bytes(b"")
            with mock.patch.dict(os.environ, {"CLIO_AGENT_CACHE_DIR": tmp}):
                found = find_chromium.find()
        self.assertTrue(found["found"])
        self.assertEqual(found["playwright"], "1.10.0")


if __name__ == "__main__":
    unittest.main()
