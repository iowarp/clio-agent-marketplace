"""Genomics Review Agent (archived): one plugin and its subagents."""

from clio_agent.sdk import Agent


class GenomicsReview(Agent):
    """Coordinates cohort QC, reference review, and VCF variant handoff for small genomics studies."""

    id = "genomics-review"
    version = "0.1.0"
    name = "Genomics Review Agent"
    role = "a genomics review coordinator for cohort QC, reference review and VCF variant handoff"
    description = "Coordinates cohort QC, reference review, and VCF variant handoff for small genomics studies."
    plugins = Agent.plugins + ["genomics-review", "delegation"]
