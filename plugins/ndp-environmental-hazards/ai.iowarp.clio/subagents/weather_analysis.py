"""NDP Weather CSV Analysis Expert: a defined subagent of ndp-environmental-hazards."""

from clio_agent.sdk import PromptFile, Subagent

weather_analysis = Subagent(
    "weather_analysis",
    prompt=PromptFile("prompt/subagents/weather_analysis.md"),
    description="NDP Weather CSV Analysis Expert",
    plugins=["ndp"],
    tools=[
        "ndp_search_datasets",
        "ndp_get_dataset_details",
        "ndp_stage_resource",
        "ndp_profile_csv_resource",
    ],
    structured_outputs={"evidence": True, "errors": True},
)
