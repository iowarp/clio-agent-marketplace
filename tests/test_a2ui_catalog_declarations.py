"""Per-agent A2UI catalog allowlists across the packs that produce A2UI.

clio-agent 0.9.4.17 makes an agent's ``a2ui_catalogs`` the COMPLETE list of
catalogs it may produce against, in preference order: nothing is implicit,
the builtin ``clio-workspace`` and ``basic`` catalogs included. A pack must
therefore list what it uses. Only a pack whose list names a PACK-LOCAL catalog
needs the ``requires.clio_agent`` floor: an older runtime reads the list form
as no pack catalogs, which drops that catalog, while a builtins-only list
still gets the builtins an older runtime always offered.

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

#: Every shipped pack and the catalogs it declares, in the declared
#: (preference) order. Every shipped agent keeps A2UI through clio-workspace.
EXPECTED_CATALOGS: dict[str, list[Any]] = {
    "base-agent": ["clio-workspace"],
    "cluster-operator": ["clio-workspace"],
    "data-semantics": ["clio-workspace"],
    "deep-researcher": ["clio-workspace"],
    "document-production": ["clio-workspace"],
    "earthscope-flat": ["clio-workspace"],
    "earthscope-gnss-region": ["clio-workspace"],
    "factorio": ["clio-workspace"],
    "factorio-flat": ["clio-workspace"],
    "phenotype": ["clio-workspace"],
    "spotter-ai": ["clio-workspace"],
    "wildfire-smoke-impact-review": ["clio-workspace"],
    "earthscope-single-agent": [
        "clio-workspace",
        {"earthscope-stations": "catalogs/earthscope-stations"},
    ],
}

#: The builtin catalog names clio-agent accepts in an ``a2ui_catalogs`` list.
BUILTIN_CATALOGS = frozenset({"clio-workspace", "basic"})

FLOOR = ">=0.9.4.17"

#: The packs whose list names a pack-local catalog -- the only ones with a floor.
FLOORED_PACKS = frozenset({"earthscope-single-agent"})


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


def _shipped_packs() -> list[Path]:
    """Every top-level pack directory (one carrying an ``AGENT.md``)."""

    return sorted(path.parent for path in MARKETPLACE.glob("*/AGENT.md"))


def _root_expert_kind(pack: Path) -> str | None:
    """The ``module.kind`` of a pack's root expert, or ``None`` if undeclared."""

    root_id = _top_level_block(pack / "AGENT.md", "root_expert") or _top_level_block(
        pack / "AGENT.md", "default_expert"
    )
    for expert in sorted((pack / "experts").glob("*.md")):
        if _top_level_block(expert, "id") == root_id:
            module = _top_level_block(expert, "module")
            return module.get("kind") if isinstance(module, dict) else None
    return None


class A2UICatalogDeclarationTests(unittest.TestCase):
    """Each shipped pack lists its catalogs and carries the floor."""

    def test_every_react_root_pack_declares_clio_workspace(self) -> None:
        """A react root is where A2UI producer tools attach; without a declared
        catalog clio-agent 0.9.4.17 attaches none, so a new pack that forgot the
        list would silently lose A2UI."""

        react_roots = [pack for pack in _shipped_packs() if _root_expert_kind(pack) == "react"]
        self.assertTrue(react_roots)
        for pack in react_roots:
            with self.subTest(pack=pack.name):
                declared = _top_level_block(pack / "AGENT.md", "a2ui_catalogs") or []
                self.assertIn("clio-workspace", declared)

    def test_the_expected_table_covers_every_shipped_pack(self) -> None:
        self.assertEqual(sorted(EXPECTED_CATALOGS), [pack.name for pack in _shipped_packs()])

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

    def test_only_packs_declaring_a_pack_catalog_carry_the_floor(self) -> None:
        for pack, expected in EXPECTED_CATALOGS.items():
            with self.subTest(pack=pack):
                requires = _top_level_block(MARKETPLACE / pack / "AGENT.md", "requires")
                names_pack_catalog = any(isinstance(entry, dict) for entry in expected)
                self.assertEqual(names_pack_catalog, pack in FLOORED_PACKS)
                if pack in FLOORED_PACKS:
                    self.assertEqual(requires, {"clio_agent": FLOOR})
                else:
                    self.assertNotEqual((requires or {}).get("clio_agent"), FLOOR)


if __name__ == "__main__":
    unittest.main()
