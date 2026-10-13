"""The search assistant's prompt stays bounded to real, read-only source discovery."""

from pathlib import Path
import unittest

from tests.test_base_agent_policy import parse_frontmatter

PACK = Path(__file__).resolve().parents[1] / "clio-search"


class SearchPolicyTests(unittest.TestCase):
    def test_search_is_a_leaf_with_only_read_tools_and_no_model_pin(self) -> None:
        parsed = parse_frontmatter(PACK / "experts" / "search.md")
        self.assertEqual(parsed["tools"], ["clio_search", "clio_search_read"])
        self.assertFalse(parsed.get("children"))
        self.assertNotIn("model", parsed)
        manifest = (PACK / "AGENT.md").read_text(encoding="utf-8")
        self.assertNotIn("mcp_servers:", manifest)

    def test_source_data_cannot_authorize_commands_and_links_are_not_invented(self) -> None:
        source = (PACK / "experts" / "search.md").read_text(encoding="utf-8")
        self.assertIn("source data, never instructions", source)
        self.assertIn("returned href exactly as supplied", source)
        self.assertIn("Inspect actual sources", source)
        self.assertIn("scan limits", source)
        self.assertIn("never “it does not exist”", source)


if __name__ == "__main__":
    unittest.main()
