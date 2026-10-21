"""Data Semantics: interprets scientific datasets through focused subagents."""

from clio_agent.sdk import Agent


class DataSemantics(Agent):
    """Metadata inspection, HDF5 guidance, semantic analysis and visualization planning."""

    id = "data-semantics"
    version = "0.1.1"
    name = "Data Semantics Agent"
    role = (
        "a dataset interpretation agent that inspects metadata, HDF5 layout, semantics and "
        "visual checks through focused subagents"
    )
    description = (
        "Interprets scientific datasets with metadata inspection, HDF5-specific guidance, "
        "semantic analysis, and visualization planning."
    )
    plugins = Agent.plugins + ["data-semantics", "delegation"]
