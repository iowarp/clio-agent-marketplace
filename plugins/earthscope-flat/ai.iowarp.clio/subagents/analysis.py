"""EarthScope Scientific Analysis Expert: a defined subagent of earthscope-flat."""

from clio_agent.sdk import PromptFile, Subagent

analysis = Subagent(
    "analysis",
    prompt=PromptFile("prompt/subagents/analysis.md"),
    description="The single self-sufficient ANALYSIS expert. Profiles the STAGED GNSS time-series CSV with pandas_profile_csv and reasons about station/network suitability from that evidence. Produces workflow_state.profile (+ network_analysis). Needs a staged CSV from ndp.",
    plugins=["pandas"],
    tools=["pandas_profile_csv"],
    structured_outputs={"workflow_state": True, "evidence": True, "errors": True},
)
