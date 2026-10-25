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

    def _plugin(self, name: str) -> Path:
        """Create ``plugins/<name>/plugin.json`` and return the plugin folder."""
        plugin = self.root / "plugins" / name
        _write(plugin / "plugin.json", "{}\n")
        return plugin

    def test_denylist_hit_is_reported_without_opt_in(self) -> None:
        """A denylisted literal fails the plugin even with strict rules off."""
        plugin = self._plugin("gnss")
        _write(plugin / "lint-denylist.txt", "# station ids\n\nP475\n")
        _write(
            plugin / "ai.iowarp.clio" / "prompt" / "main.md",
            "---\nid: gnss.main\nsection: domain\n---\nUse station P475.\n",
        )
        _write(plugin / "skills" / "profile" / "run.py", "STATION = 'P475'\n")

        findings = find_literals(self.root)

        self.assertEqual(_rules(findings), ["denylist", "denylist"])
        self.assertEqual(findings[0].line, 5)
        self.assertEqual(findings[0].excerpt, "P475")
        self.assertEqual(findings[1].path.name, "run.py")

    def test_subagent_prompts_are_scanned(self) -> None:
        """Plain prompt files (subagent prompts) are prompt text too."""
        plugin = self._plugin("gnss")
        _write(plugin / "lint-denylist.txt", "P475\n")
        _write(plugin / "ai.iowarp.clio" / "prompt" / "subagents" / "data.md", "Stage P475.\n")

        findings = find_literals(self.root)

        self.assertEqual([(f.rule, f.line) for f in findings], [("denylist", 1)])

    def test_strict_rules_are_off_by_default(self) -> None:
        """Plugins without a marker are not held to the generic rules."""
        _write(self._plugin("legacy") / "skills" / "x" / "SKILL.md", _STRICT_LINES)

        self.assertEqual(find_literals(self.root), [])

    def test_marker_file_enables_strict_rules(self) -> None:
        """A ``.lint-l3`` marker opts a plugin into every generic rule."""
        plugin = self._plugin("strict")
        _write(plugin / ".lint-l3", "")
        _write(plugin / "skills" / "x" / "SKILL.md", _STRICT_LINES)

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
        """``--strict-pack`` opts in one named plugin only."""
        for name in ("a", "b"):
            _write(self._plugin(name) / "skills" / "x" / "SKILL.md", "Seen on 2023-01-02.\n")

        findings = find_literals(self.root, ["a"])

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].path.parts[-4], "a")

    def test_generic_names_and_templates_pass_strict_rules(self) -> None:
        """Placeholders, digit-free names and ordinary prose are not leaks."""
        plugin = self._plugin("strict")
        _write(plugin / ".lint-l3", "")
        _write(
            plugin / "skills" / "x" / "SKILL.md",
            "Open output.h5, <station>.csv, {id}_2024.parquet or *.nc.\n"
            "Stage it at `<workspace>/<station id>.*.csv`.\n"
            "Use a 1920x1080 image and hex 0x1F; 3 of 4 rows.\n",
        )

        self.assertEqual(find_literals(self.root), [])

    def test_allow_comment_skips_line(self) -> None:
        """``lint: allow-literal`` exempts exactly the line that carries it."""
        plugin = self._plugin("strict")
        _write(plugin / ".lint-l3", "")
        _write(plugin / "lint-denylist.txt", "P475\n")
        _write(
            plugin / "skills" / "x" / "SKILL.md",
            "Example P475 on 2024-01-01 <!-- lint: allow-literal -->\nNever P475.\n",
        )

        findings = find_literals(self.root)

        self.assertEqual([(f.rule, f.line) for f in findings], [("denylist", 2)])

    def test_skips_tests_evals_fixtures_and_non_plugin_dirs(self) -> None:
        """Test data, folders without plugin.json and repository tooling are not scanned."""
        _write(self.root / "scripts" / "skills" / "x" / "SKILL.md", "P475\n")
        _write(self.root / "plugins" / "loose" / "lint-denylist.txt", "P475\n")
        _write(self.root / "plugins" / "loose" / "skills" / "x" / "SKILL.md", "P475\n")
        plugin = self._plugin("pack")
        _write(plugin / "lint-denylist.txt", "P475\n")
        _write(plugin / "tests" / "test_x.py", "P475\n")
        _write(plugin / "evals" / "case.md", "P475\n")
        _write(plugin / "skills" / "x" / "fixtures" / "data.txt", "P475\n")
        _write(plugin / "skills" / "x" / "evals" / "case.md", "P475\n")
        _write(plugin / "README.md", "P475\n")
        _write(plugin / "ai.iowarp.clio" / "a2ui" / "c" / "instructions.md", "P475\n")

        self.assertEqual(find_literals(self.root), [])

    def test_fragment_frontmatter_is_not_scanned(self) -> None:
        """Only a fragment's body is prompt text; its frontmatter is configuration."""
        plugin = self._plugin("pack")
        _write(plugin / "lint-denylist.txt", "P475\n")
        _write(
            plugin / "ai.iowarp.clio" / "prompt" / "x.md",
            "---\nid: pack.P475\nsection: domain\n---\nBody mentions P475.\n",
        )

        findings = find_literals(self.root)

        self.assertEqual([(f.rule, f.line) for f in findings], [("denylist", 5)])

    def test_main_reports_and_exits_nonzero(self) -> None:
        """The CLI prints ``path:line: rule: excerpt`` and exits 1 on findings."""
        _write(self._plugin("p") / "skills" / "x" / "SKILL.md", "ok\nsee 2020-05-06\n")
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            clean = main([str(self.root)])
            dirty = main([str(self.root), "--strict-pack", "p"])

        self.assertEqual(clean, 0)
        self.assertEqual(dirty, 1)
        self.assertIn("plugins/p/skills/x/SKILL.md:2: iso-date: 2020-05-06", output.getvalue())

    def test_main_rejects_unknown_strict_pack(self) -> None:
        """A typo in ``--strict-pack`` is a usage error, not a silent pass."""
        self._plugin("p")

        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as raised,
        ):
            main([str(self.root), "--strict-pack", "missing"])

        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
