"""MCP Calculator Smoke Agent (archived): one plugin and its subagents."""

from clio_agent.sdk import Agent


class McpCalculatorSmoke(Agent):
    """Minimal smoke-test agent that packages a plugin-local MCP server for marketplace launch-semantics validation."""

    id = "mcp-calculator-smoke"
    version = "0.1.0"
    name = "MCP Calculator Smoke Agent"
    role = "a marketplace smoke-test agent for a plugin-local MCP server"
    description = "Minimal smoke-test agent that packages a plugin-local MCP server for marketplace launch-semantics validation."
    plugins = Agent.plugins + ["mcp-calculator-smoke"]
