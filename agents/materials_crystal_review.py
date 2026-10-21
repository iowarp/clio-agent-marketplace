"""Materials Crystal Review Agent (archived): one plugin and its subagents."""

from clio_agent.sdk import Agent


class MaterialsCrystalReview(Agent):
    """Reviews CIF crystal structures for structure provenance and simulation readiness."""

    id = "materials-crystal-review"
    version = "0.1.0"
    name = "Materials Crystal Review Agent"
    role = "a materials reviewer of CIF crystal structures for provenance and simulation readiness"
    description = (
        "Reviews CIF crystal structures for structure provenance and simulation readiness."
    )
    plugins = Agent.plugins + ["materials-crystal-review", "delegation"]
