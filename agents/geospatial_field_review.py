"""Geospatial Field Review Agent (archived): one plugin and its subagents."""

from clio_agent.sdk import Agent


class GeospatialFieldReview(Agent):
    """Reviews GeoJSON field-site data for map-overlay and spatial-analysis readiness."""

    id = "geospatial-field-review"
    version = "0.1.0"
    name = "Geospatial Field Review Agent"
    role = "a geospatial reviewer of GeoJSON field-site data for map-overlay and spatial-analysis readiness"
    description = "Reviews GeoJSON field-site data for map-overlay and spatial-analysis readiness."
    plugins = Agent.plugins + ["geospatial-field-review", "delegation"]
