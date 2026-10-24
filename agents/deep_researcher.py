"""Deep Researcher: cited web research run as the deep-research flow."""

from clio_agent.sdk import Agent


class DeepResearcher(Agent):
    """A coordinator that starts the deep-research flow and delivers its verified report."""

    id = "deep-researcher"
    version = "0.3.0"
    name = "Deep Researcher"
    role = (
        "a coordinator that answers hard questions with cited web research, verified by an "
        "independent critic"
    )
    description = (
        "Model-agnostic deep web research run as a flow: a planner chooses the research "
        "directions, web researchers investigate them in parallel, an independent web-enabled "
        "critic verifies every claim against fetched sources and names the gaps, the gaps are "
        "researched within a bounded number of rounds, and the report is written only from "
        "verified claims and delivered as a Markdown artifact with inline citations, the "
        "unresolved questions and the rejected claims."
    )
    plugins = Agent.plugins + ["orchestration", "deep-research"]
