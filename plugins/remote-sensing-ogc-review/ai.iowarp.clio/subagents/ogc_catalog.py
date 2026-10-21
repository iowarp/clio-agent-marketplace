"""OGC Catalog Expert: a defined subagent of remote-sensing-ogc-review."""

from clio_agent.sdk import PromptFile, Subagent

ogc_catalog = Subagent(
    "ogc_catalog",
    prompt=PromptFile("prompt/subagents/ogc_catalog.md"),
    description="OGC Catalog Expert: ogc api features",
    plugins=[],
    tools=["ogc_features_query", "load_skill"],
)
