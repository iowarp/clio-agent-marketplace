"""SPOTTER AI: forensic watcher and provider-aware provenance investigator."""

from clio_agent.sdk import Agent


class SpotterAI(Agent):
    """Live anomaly surveillance, containment and evidence-backed provenance investigation."""

    id = "spotter-ai"
    version = "0.4.0"
    name = "SPOTTER AI (forensic watcher)"
    role = (
        "a forensic watcher that detects and contains anomalous workload runs and investigates "
        "execution and artifact provenance across the configured stores"
    )
    description = (
        "Live anomaly surveillance, containment, and evidence-backed provenance investigation "
        "across the reference phenotype campaign, Flowcept, CMF, and native stores."
    )
    plugins = Agent.plugins + ["spotter"]
