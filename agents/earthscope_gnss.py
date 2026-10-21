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


class EarthscopeFlat(Agent):
    """The small-model-friendly flat variant: one root over four self-sufficient subagents."""

    id = "earthscope-flat"
    version = "0.1.1"
    name = "EarthScope (Flat)"
    role = (
        "an EarthScope GNSS region orchestrator over four self-sufficient subagents that "
        "writes the grounded final answer"
    )
    description = (
        "Small-model-friendly flat variant of earthscope-gnss-region: one root over four "
        "self-sufficient subagents. Resolves a geography, discovers and stages an NDP "
        "EarthScope GNSS station CSV, profiles it, and produces an evidence-backed PNG. Every "
        "subagent inherits the provider and model selected for the session."
    )
    plugins = Agent.plugins + ["earthscope-flat", "earthscope", "delegation"]
