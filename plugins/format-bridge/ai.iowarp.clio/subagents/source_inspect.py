"""Source Inspect Expert: a defined subagent of format-bridge."""

from clio_agent.sdk import PromptFile, Subagent

source_inspect = Subagent(
    "source_inspect",
    prompt=PromptFile("prompt/subagents/source_inspect.md"),
    description="Source Inspect Expert: scientific source format inspection",
    plugins=["hdf5"],
    tools=["hdf5_list_datasets", "hdf5_analyze_file", "hdf5_analyze_dataset", "load_skill"],
)
