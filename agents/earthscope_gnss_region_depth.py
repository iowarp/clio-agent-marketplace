"""EarthScope GNSS Region Depth Topology Agent (archived): one plugin and its subagents."""

from clio_agent.sdk import Agent


class EarthscopeGnssDepth(Agent):
    """Depth-topology variant for resolving geography, discovering NDP EarthScope GNSS resources, profiling station CSV time series, and producing evidence-backed artifacts."""

    id = "earthscope-gnss-region-depth"
    version = "0.1.0"
    name = "EarthScope GNSS Region Depth Topology Agent"
    role = "an EarthScope GNSS region orchestrator over a deep subagent topology"
    description = "Depth-topology variant for resolving geography, discovering NDP EarthScope GNSS resources, profiling station CSV time series, and producing evidence-backed artifacts."
    plugins = Agent.plugins + ["earthscope-gnss-region-depth", "delegation"]
