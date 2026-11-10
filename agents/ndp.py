"""NDP: CLIO's standard agent with the National Data Platform package."""

from .standard import StandardAgent


class Ndp(StandardAgent):
    """The standard agent plus NDP catalog search, access and Endpoints (L2 source)."""

    id = "ndp"
    version = "1.0.0"
    name = "NDP"
    role = (
        "an autonomous scientific coding and data assistant that finds, attaches and analyzes "
        "National Data Platform data in the user's workspace"
    )
    description = (
        "CLIO's standard agent with the National Data Platform: search NDP organizations, "
        "datasets and resources, attach and download them, analyze the data, and query or "
        "publish to NDP Endpoints. Works without any MCP server."
    )
    plugins = StandardAgent.plugins + ["ndp"]
