"""CLIO's standard agent and the science base other agents build on."""

from clio_agent.sdk import Agent


class StandardAgent(Agent):
    """The default agent: grounded workspace work with no hidden routing hierarchy."""

    id = "standard"
    version = "1.0.0"
    name = "CLIO"
    role = "an autonomous scientific coding and data assistant working in the user's workspace"
    description = (
        "CLIO's general-purpose agent: workspace files, a shell, the web, documents, "
        "interactive visuals, connected data, general subagents, workflows and flows."
    )
    plugins = Agent.plugins + [
        "workspace",
        "shell",
        "web",
        "documents",
        "visuals",
        "connected-data",
        "delegation",
        "orchestration",
    ]


class ScienceAgent(StandardAgent):
    """A base for domain science agents: the standard agent plus scientific method."""

    id = "science"
    name = "CLIO Science"
    role = "a scientific research assistant that grounds every claim in inspected data"
    description = (
        "The standard agent's capabilities plus general scientific practice and the study "
        "log, as a base for domain science agents."
    )
    plugins = StandardAgent.plugins + ["scientific-method", "science-log"]
