"""Phenotype Campaign: the synthetic workload SPOTTER AI watches."""

from clio_agent.sdk import Agent


class Phenotype(Agent):
    """Operates the synthetic plant-phenotyping campaign and reports per-run metrics."""

    id = "phenotype"
    version = "0.1.1"
    name = "Phenotype (synthetic workload)"
    role = (
        "the operator of a synthetic plant-phenotyping campaign that reports per-run metrics "
        "honestly and relays quarantine halts verbatim"
    )
    description = (
        "Synthetic plant-phenotyping campaign operator, the reference stand-in workload for "
        "SPOTTER AI. Runs a deterministic 5-stage pipeline (ingest -> calibrate -> segment -> "
        "extract traits -> predict) with full provenance capture per stage execution."
    )
    plugins = Agent.plugins + ["phenotype"]
