"""EarthScope GNSS Region Width Topology Agent (archived): one plugin and its subagents."""

from clio_agent.sdk import Agent


class EarthscopeGnssWidth(Agent):
    """Width-topology variant for resolving geography, discovering NDP EarthScope GNSS resources, profiling station CSV time series, and producing evidence-backed artifacts."""

    id = "earthscope-gnss-region-width"
    version = "0.1.0"
    name = "EarthScope GNSS Region Width Topology Agent"
    role = "an EarthScope GNSS region orchestrator over a wide subagent topology"
    description = "Width-topology variant for resolving geography, discovering NDP EarthScope GNSS resources, profiling station CSV time series, and producing evidence-backed artifacts."
    plugins = Agent.plugins + ["earthscope-gnss-region-width", "delegation"]
