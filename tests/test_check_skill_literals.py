"""Tests for the marketplace skill-literal (L3 leakage) policy."""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts.check_skill_literals import find_literals, main

_STRICT_LINES = (
    "Run 2024-06-07 showed drift.\n"
    "Values are ~40× too small.\n"
    "Amplitudes were 40x too low.\n"
    "Spread was 30–50× the baseline.\n"
    "Sample 12__345__678 was dropped.\n"
    "Read P475.CI.LY_.20.csv first.\n"
)


def _write(path: Path, text: str) -> None:
    """Write ``text`` to ``path``, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _rules(findings: list) -> list[str]:
    """Return the rule names of ``findings`` in report order."""
    return [finding.rule for finding in findings]


class SkillLiteralPolicyTests(unittest.TestCase):
    """Exercise denylist, opt-in strict rules, allow comments and skips."""

    def setUp(self) -> None:
        """Create an empty temporary marketplace root."""
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        """Remove the temporary marketplace root."""
        self._tmp.cleanup()

    def test_denylist_hit_is_reported_without_opt_in(self) -> None:
        """A denylisted literal fails the pack even with strict rules off."""
        pack = self.root / "gnss"
        _write(pack / "lint-denylist.txt", "# station ids\n\nP475\n")
        _write(pack / "experts" / "main.md", "---\nid: main\n---\nUse station P475.\n")
        _write(pack / "skills" / "profile" / "run.py", "STATION = 'P475'\n")

        findings = find_literals(self.root)

        self.assertEqual(_rules(findings), ["denylist", "denylist"])
        self.assertEqual(findings[0].line, 4)
        self.assertEqual(findings[0].excerpt, "P475")
        self.assertEqual(findings[1].path.name, "run.py")

    def test_strict_rules_are_off_by_default(self) -> None:
        """Existing packs without a marker are not held to the generic rules."""
        _write(self.root / "legacy" / "skills" / "x" / "SKILL.md", _STRICT_LINES)

        self.assertEqual(find_literals(self.root), [])

    def test_marker_file_enables_strict_rules(self) -> None:
        """A ``.lint-l3`` marker opts a pack into every generic rule."""
        pack = self.root / "strict"
        _write(pack / ".lint-l3", "")
        _write(pack / "skills" / "x" / "SKILL.md", _STRICT_LINES)

        findings = find_literals(self.root)

        self.assertEqual(
            _rules(findings),
            [
                "iso-date",
                "measured-magnitude",
                "measured-magnitude",
                "measured-magnitude",
                "sample-key",
                "dataset-file",
            ],
        )
        self.assertEqual(findings[-1].excerpt, "P475.CI.LY_.20.csv")

    def test_strict_pack_flag_enables_strict_rules(self) -> None:
        """``--strict-pack`` opts in one named pack only."""
        _write(self.root / "a" / "experts" / "main.md", "Seen on 2023-01-02.\n")
        _write(self.root / "b" / "experts" / "main.md", "Seen on 2023-01-02.\n")

        findings = find_literals(self.root, ["a"])

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].path.parts[-3], "a")

    def test_generic_names_and_templates_pass_strict_rules(self) -> None:
        """Placeholders, digit-free names and ordinary prose are not leaks."""
        pack = self.root / "strict"
        _write(pack / ".lint-l3", "")
        _write(
            pack / "skills" / "x" / "SKILL.md",
            "Open output.h5, <station>.csv, {id}_2024.parquet or *.nc.\n"
            "Stage it at `<workspace>/<station id>.*.csv`.\n"
            "Use a 1920x1080 image and hex 0x1F; 3 of 4 rows.\n",
        )

        self.assertEqual(find_literals(self.root), [])

    def test_allow_comment_skips_line(self) -> None:
        """``lint: allow-literal`` exempts exactly the line that carries it."""
        pack = self.root / "strict"
        _write(pack / ".lint-l3", "")
        _write(pack / "lint-denylist.txt", "P475\n")
        _write(
            pack / "experts" / "main.md",
            "Example P475 on 2024-01-01 <!-- lint: allow-literal -->\nNever P475.\n",
        )

        findings = find_literals(self.root)

        self.assertEqual([(f.rule, f.line) for f in findings], [("denylist", 2)])

    def test_skips_pack_tests_evals_fixtures_and_non_pack_dirs(self) -> None:
        """Test data and repository tooling are outside the scanned surface."""
        _write(self.root / "old" / "p" / "experts" / "main.md", "P475\n")
        _write(self.root / "old" / "lint-denylist.txt", "P475\n")
        pack = self.root / "pack"
        _write(pack / "lint-denylist.txt", "P475\n")
        _write(pack / "tests" / "test_x.py", "P475\n")
        _write(pack / "evals" / "case.md", "P475\n")
        _write(pack / "skills" / "x" / "fixtures" / "data.txt", "P475\n")
        _write(pack / "skills" / "x" / "evals" / "case.md", "P475\n")
        _write(pack / "README.md", "P475\n")
        _write(pack / "experts" / "nested" / "deep.md", "P475\n")

        self.assertEqual(find_literals(self.root), [])

    def test_agent_frontmatter_is_not_scanned(self) -> None:
        """Only the AGENT.md body is prompt text; frontmatter is configuration."""
        pack = self.root / "pack"
        _write(pack / "lint-denylist.txt", "P475\n")
        _write(pack / "AGENT.md", "---\nid: P475\n---\nBody mentions P475.\n")

        findings = find_literals(self.root)

        self.assertEqual([(f.rule, f.line) for f in findings], [("denylist", 4)])

    def test_main_reports_and_exits_nonzero(self) -> None:
        """The CLI prints ``path:line: rule: excerpt`` and exits 1 on findings."""
        _write(self.root / "p" / "experts" / "main.md", "ok\nsee 2020-05-06\n")
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            clean = main([str(self.root)])
            dirty = main([str(self.root), "--strict-pack", "p"])

        self.assertEqual(clean, 0)
        self.assertEqual(dirty, 1)
        self.assertIn("p/experts/main.md:2: iso-date: 2020-05-06", output.getvalue())

    def test_main_rejects_unknown_strict_pack(self) -> None:
        """A typo in ``--strict-pack`` is a usage error, not a silent pass."""
        (self.root / "p").mkdir()

        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as raised,
        ):
            main([str(self.root), "--strict-pack", "missing"])

        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
