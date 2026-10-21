"""Proteomics Review Agent (archived): one plugin and its subagents."""

from clio_agent.sdk import Agent


class ProteomicsMzmlReview(Agent):
    """Reviews mzML runs and LFQ protein-intensity matrices for proteomics handoff readiness."""

    id = "proteomics-mzml-review"
    version = "0.2.0"
    name = "Proteomics Review Agent"
    role = "a proteomics reviewer of mzML runs and LFQ protein-intensity matrices"
    description = (
        "Reviews mzML runs and LFQ protein-intensity matrices for proteomics handoff readiness."
    )
    plugins = Agent.plugins + ["proteomics-mzml-review", "delegation"]
