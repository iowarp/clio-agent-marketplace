"""Scientific Format Bridge Agent (archived): one plugin and its subagents."""

from clio_agent.sdk import Agent


class FormatBridge(Agent):
    """Converts scientific HDF5 datasets to downstream-readable formats with dtype policy and integrity evidence."""

    id = "format-bridge"
    version = "0.1.0"
    name = "Scientific Format Bridge Agent"
    role = "a scientific format bridge that converts HDF5 data to downstream formats with dtype policy and integrity evidence"
    description = "Converts scientific HDF5 datasets to downstream-readable formats with dtype policy and integrity evidence."
    plugins = Agent.plugins + ["format-bridge", "delegation"]
