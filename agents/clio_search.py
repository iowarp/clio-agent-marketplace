"""CLIO Search: read-only answers across the connected service."""

from clio_agent.sdk import Agent


class ClioSearch(Agent):
    """Discovery across conversations, message passages and workspace files."""

    id = "clio-search"
    version = "0.1.0"
    name = "CLIO Search"
    role = (
        "a read-only search assistant for the connected CLIO service's conversations, "
        "message passages and workspace files"
    )
    description = (
        "Read-only answers and discovery across the connected CLIO service's conversations, "
        "message passages, and workspace files, with real navigable source links."
    )
    plugins = Agent.plugins + ["clio-search"]
