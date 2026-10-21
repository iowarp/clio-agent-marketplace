"""Remote Sensing OGC Review Agent (archived): one plugin and its subagents."""

from clio_agent.sdk import Agent


class RemoteSensingOgcReview(Agent):
    """Reviews remote sensing metadata through an explicitly enabled OGC API MCP descriptor."""

    id = "remote-sensing-ogc-review"
    version = "0.1.0"
    name = "Remote Sensing OGC Review Agent"
    role = "a remote sensing catalog reviewer working through an OGC API Features server"
    description = (
        "Reviews remote sensing metadata through an explicitly enabled OGC API MCP descriptor."
    )
    plugins = Agent.plugins + ["remote-sensing-ogc-review", "delegation"]
