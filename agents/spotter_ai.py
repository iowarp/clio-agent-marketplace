"""SPOTTER: a forensic watcher over a working CLIO session."""

from clio_agent.sdk import Agent
from clio_agent.sdk.agent import CORE_PLUGIN


class SpotterAI(Agent):
    """Watches a session's recorded provenance and alerts the person to unexplained deviations."""

    id = "spotter-ai"
    version = "0.5.0"
    name = "SPOTTER"
    role = "a forensic watcher that guards a working CLIO session using its recorded provenance"
    description = (
        "Watches a working CLIO session through its recorded provenance (Flowcept, CMF or "
        "CLIO's native journal, plus captured attention), investigates unexplained deviations "
        "and raises evidence-backed alerts for the person to decide on."
    )
    # No memory plugin: its memory and session-recall tools are not how SPOTTER reads the
    # watched session (review_activity is), and a small model wanders into them. Every
    # agent must carry core.
    plugins = [CORE_PLUGIN, "spotter"]
