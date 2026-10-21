"""Geospatial Resolution Expert: a defined subagent of earthscope-gnss."""

from clio_agent.sdk import PromptFile, Subagent

geospatial = Subagent(
    "geospatial",
    prompt=PromptFile("prompt/subagents/geospatial.md"),
    description="Resolves the requested place into a GROUNDED region (center lat/lon, radius or bbox). Calls the geocode tool for a place name; uses coordinates verbatim when the request already supplies them. Produces workflow_state.geospatial. Runs FIRST.",
    plugins=["geo"],
    tools=["geo_geocode"],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
