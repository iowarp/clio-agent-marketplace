"""The fixture's own reviewer: a defined subagent, for summoning tests."""

from clio_agent.sdk import PromptFile, Subagent

fixture_reviewer = Subagent(
    "fixture-reviewer",
    prompt=PromptFile("prompt/subagents/fixture_reviewer.md"),
    description="Reads one workspace file and lists its problems. Use to check a file.",
    plugins=["workspace"],
    tools=["fs_read_file", "fs_list_directory", "fs_search_text"],
    effects="read",
    max_iters=16,
)
