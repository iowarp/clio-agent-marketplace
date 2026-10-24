"""CLIO Search: answers from the connected service's conversations and files."""

from clio_agent.sdk import Agent


class ClioSearch(Agent):
    """Discovery across conversations, message passages and workspace files."""

    id = "clio-search"
    version = "0.2.0"
    name = "CLIO Search"
    role = (
        "a search assistant for the connected CLIO service's conversations, message passages "
        "and workspace files"
    )
    description = (
        "Answers and discovery across the connected CLIO service's conversations, message "
        "passages, and workspace files, with real navigable source links."
    )
    plugins = Agent.plugins + ["clio-search"]
