"""Commands fixture agent: the standard agent's plugins plus the command and summoning fixtures."""

from clio_agent.sdk import Agent


class CommandsFixture(Agent):
    """Test agent for the command table, skills as commands, summoning and MCP prompts."""

    id = "commands-fixture"
    version = "0.1.0"
    name = "Commands Fixture Agent"
    role = "a test agent for CLIO's commands and direct summoning"
    description = (
        "The standard agent's plugins plus commands-fixture, commands-clash and "
        "prompts-fixture, for the command table, clashes, skills as commands, summoning "
        "subagents and servers, and MCP prompts as commands."
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
        "browser",
        "commands-fixture",
        "commands-clash",
        "prompts-fixture",
    ]
