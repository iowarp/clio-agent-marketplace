"""EarthScope GNSS region agents: the hierarchical tree and the flat variant."""

from clio_agent.sdk import Agent


class EarthscopeGnss(Agent):
    """Resolves a geography and studies its EarthScope GNSS stations through subagents."""

    id = "earthscope-gnss-region"
    version = "0.1.1"
    name = "EarthScope"
    role = (
        "an EarthScope GNSS region orchestrator that routes geography, station data, analysis "
        "and visualization work to subagents and writes the grounded final answer"
    )
    description = (
        "Resolves a requested geography, discovers NDP EarthScope GNSS resources, profiles "
        "station CSV time series, and produces evidence-backed artifacts."
    )
    plugins = Agent.plugins + ["earthscope-gnss", "earthscope", "delegation"]
