"""Dataset Metadata Expert: a defined subagent of data-semantics."""

from clio_agent.sdk import PromptFile, Subagent

data = Subagent(
    "data",
    prompt=PromptFile("prompt/subagents/data.md"),
    description="Dataset Metadata Expert",
    plugins=["hdf5", "parquet", "pandas"],
    tools=[
        "hdf5_list_available_hdf5_files",
        "hdf5_analyze_dataset_structure",
        "parquet_summarize_tool",
        "pandas_profile_csv",
        "load_skill",
    ],
)
