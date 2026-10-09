"""Guard the default agent's generated-figure presentation guidance."""

from pathlib import Path


def test_base_agent_displays_registered_visual_artifacts_with_a2ui() -> None:
    """Generated figures are visible views with retained downloadable files."""
    prompt = (Path(__file__).resolve().parents[1] / "base-agent" / "experts" / "base.md").read_text(
        encoding="utf-8"
    )
    assert "PNG," in prompt and "JPEG, or SVG" in prompt
    assert "active A2UI catalog's Image component" in prompt
    assert "present-interactive-analysis" in prompt
    assert "registered artifact reference" in prompt
    assert "available for download" in prompt
    assert "Show each figure once in A2UI" in prompt
    assert "Give a new figure its own image view" in prompt
    assert "Reuse that image view for revisions" in prompt
