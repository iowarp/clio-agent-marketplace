"""Deep Researcher: agent-driven deep web research with a critic gate."""

from clio_agent.sdk import Agent


class DeepResearcher(Agent):
    """A flat coordinator over repeatable web researchers and an independent critic."""

    id = "deep-researcher"
    version = "0.2.0"
    name = "Deep Researcher"
    role = (
        "a coordinator that answers hard questions with cited web research, verified by an "
        "independent critic"
    )
    description = (
        "Model-agnostic, agent-driven deep web research. A flat coordinator dynamically fans "
        "out as many web researchers as the question needs, sends the assembled evidence "
        "through an independent web-enabled critic, closes material gaps, and creates a clean "
        "Markdown report artifact with inline citations and an auditable source ledger."
    )
    plugins = Agent.plugins + ["deep-research"]
