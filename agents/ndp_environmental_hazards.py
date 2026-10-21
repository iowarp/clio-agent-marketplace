"""NDP Environmental Hazards Agent (archived): one plugin and its subagents."""

from clio_agent.sdk import Agent


class NdpEnvironmentalHazards(Agent):
    """Discovers live NDP hazard datasets, queries geospatial services, profiles weather CSVs, and produces verified artifacts."""

    id = "ndp-environmental-hazards"
    version = "0.1.0"
    name = "NDP Environmental Hazards Agent"
    role = "an environmental hazards analyst over live NDP datasets, geospatial services and weather data"
    description = "Discovers live NDP hazard datasets, queries geospatial services, profiles weather CSVs, and produces verified artifacts."
    plugins = Agent.plugins + ["ndp-environmental-hazards", "delegation"]
