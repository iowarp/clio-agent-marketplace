"""Per-agent A2UI catalog allowlists across the packs that produce A2UI.

clio-agent 0.9.4.17 makes an agent's ``a2ui_catalogs`` the COMPLETE list of
catalogs it may produce against, in preference order: nothing is implicit,
the builtin ``clio-workspace`` and ``basic`` catalogs included. A pack that
produces A2UI must therefore list what it uses, and must carry the
``requires.clio_agent`` floor, because an older runtime would ignore the list.

Dependency-free (runs under CI's bare ``model-inheritance`` interpreter): it
reads only the ``a2ui_catalogs`` and ``requires`` blocks with the strict
frontmatter subset shared with the Base Agent policy tests.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

from tests.test_base_agent_policy import _parse_mapping, _significant_lines

MARKETPLACE = Path(__file__).resolve().parents[1]

#: Every pack whose agent produces A2UI surfaces, and the catalogs it
#: declares, in the declared (preference) order.
EXPECTED_CATALOGS: dict[str, list[Any]] = {
    "base-agent": ["clio-workspace"],
    "factorio-flat": ["clio-workspace"],
    "spotter-ai": ["clio-workspace"],
    "earthscope-single-agent": [
        {"earthscope-stations": "catalogs/earthscope-stations"},
        "clio-workspace",
    ],
}

#: The builtin catalog names clio-agent accepts in an ``a2ui_catalogs`` list.
BUILTIN_CATALOGS = frozenset({"clio-workspace", "basic"})

FLOOR = ">=0.9.4.17"


def _frontmatter_lines(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines and lines[0].strip() == "---", f"{path}: missing opening fence"
    end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    return lines[1:end]


def _top_level_block(path: Path, key: str) -> Any:
    """Parse one top-level frontmatter key (and its indented children) strictly."""

    lines = _frontmatter_lines(path)
    start = next((i for i, line in enumerate(lines) if line.startswith(f"{key}:")), None)
    if start is None:
        return None
    block = [lines[start]]
    for line in lines[start + 1 :]:
        if line and not line[0].isspace() and not line.startswith("#"):
            break
        block.append(line)
    mapping, consumed = _parse_mapping(_significant_lines("\n".join(block)), 0, 0)
    return mapping[key]


class A2UICatalogDeclarationTests(unittest.TestCase):
    """Each A2UI-producing pack lists its catalogs and carries the floor."""

    def test_each_pack_declares_its_catalogs_in_preference_order(self) -> None:
        for pack, expected in EXPECTED_CATALOGS.items():
            with self.subTest(pack=pack):
                declared = _top_level_block(MARKETPLACE / pack / "AGENT.md", "a2ui_catalogs")
                self.assertEqual(declared, expected)

    def test_every_entry_is_a_builtin_name_or_an_existing_pack_directory(self) -> None:
        for pack in EXPECTED_CATALOGS:
            declared = _top_level_block(MARKETPLACE / pack / "AGENT.md", "a2ui_catalogs")
            for entry in declared:
                with self.subTest(pack=pack, entry=entry):
                    if isinstance(entry, str):
                        self.assertIn(entry, BUILTIN_CATALOGS)
                        continue
                    self.assertIsInstance(entry, dict)
                    self.assertEqual(len(entry), 1)
                    ((_, reldir),) = entry.items()
                    catalog_dir = MARKETPLACE / pack / reldir
                    for name in ("catalog.json", "catalog.clio.json", "instructions.md"):
                        self.assertTrue((catalog_dir / name).is_file(), catalog_dir / name)

    def test_basic_is_never_listed_implicitly_by_a_shipped_pack(self) -> None:
        """Basic stays renderable, but no shipped pack opts into producing it."""

        for pack in EXPECTED_CATALOGS:
            with self.subTest(pack=pack):
                declared = _top_level_block(MARKETPLACE / pack / "AGENT.md", "a2ui_catalogs")
                self.assertNotIn("basic", declared)

    def test_each_declaring_pack_requires_the_first_list_reading_clio_agent(self) -> None:
        for pack in EXPECTED_CATALOGS:
            with self.subTest(pack=pack):
                requires = _top_level_block(MARKETPLACE / pack / "AGENT.md", "requires")
                self.assertEqual(requires, {"clio_agent": FLOOR})


if __name__ == "__main__":
    unittest.main()
