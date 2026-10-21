"""NIFC: the wildfire downwind smoke-impact review agent."""

from clio_agent.sdk import Agent


class WildfireReview(Agent):
    """Finds an active wildfire impacting people downwind and renders a situational map."""

    id = "wildfire-smoke-impact-review"
    version = "0.1.1"
    name = "NIFC"
    role = (
        "a wildfire smoke-impact reviewer that fuses live fire perimeters, smoke forecasts and "
        "air-quality data through subagents and writes a grounded downwind-impact brief"
    )
    description = (
        "Finds an active wildfire impacting people downwind by fusing live fire perimeters, "
        "smoke forecast, and air-quality data, and renders a situational map."
    )
    plugins = Agent.plugins + ["wildfire", "ndp", "geo", "delegation"]
