"""Terrain Suitability Agent (archived): one plugin and its subagents."""

from clio_agent.sdk import Agent


class TerrainSuitability(Agent):
    """Finds bounded DEM or lidar terrain data and derives slope/elevation suitability evidence."""

    id = "terrain-suitability"
    version = "0.1.0"
    name = "Terrain Suitability Agent"
    role = "a terrain suitability analyst that derives slope and elevation evidence from bounded DEM or lidar data"
    description = (
        "Finds bounded DEM or lidar terrain data and derives slope/elevation suitability evidence."
    )
    plugins = Agent.plugins + ["terrain-suitability", "delegation"]
