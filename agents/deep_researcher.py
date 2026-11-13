"""Deep Researcher: cited web research run as the deep-research flow."""

from clio_agent.sdk import Agent


class DeepResearcher(Agent):
    """A coordinator that starts the deep-research flow and delivers its verified report."""

    id = "deep-researcher"
    version = "0.4.0"
    name = "Deep Researcher"
    role = (
        "a coordinator that answers hard questions with cited web research, verified by an "
        "independent critic"
    )
    description = (
        "Model-agnostic deep research run as a flow: a planner chooses the research "
        "directions, researchers investigate them in parallel on the web and in the scholarly "
        "literature (OpenAlex, Crossref, arXiv, Europe PMC, OSTI.gov, DataCite), an independent "
        "critic verifies every claim against fetched sources and names the gaps, the gaps are "
        "researched within a bounded number of rounds, and the report is written only from "
        "verified claims and delivered as a Markdown artifact with inline citations, the "
        "unresolved questions and the rejected claims."
    )
    plugins = Agent.plugins + ["orchestration", "deep-research"]
