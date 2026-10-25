"""Packaged Hook Smoke Agent (archived): one plugin and its subagents."""

from clio_agent.sdk import Agent


class HookSmoke(Agent):
    """Minimal smoke-test agent for packaged plugin hook discovery, trust, and invocation evidence."""

    id = "hook-smoke"
    version = "0.1.0"
    name = "Packaged Hook Smoke Agent"
    role = "a marketplace smoke-test agent for packaged plugin hooks"
    description = "Minimal smoke-test agent for packaged plugin hook discovery, trust, and invocation evidence."
    plugins = Agent.plugins + ["hook-smoke"]
