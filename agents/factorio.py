"""Factorio: a scientist-facing research partner for manufacturing simulation."""

from .standard import ScienceAgent


class Factorio(ScienceAgent):
    """A research partner spanning framing, evidence, simulation, review and specialists."""

    id = "factorio"
    version = "0.5.0"
    name = "Factorio"
    role = (
        "Factorio, a persistent scientific collaborator for research framing, evidence, "
        "simulation and adversarial review of manufacturing and materials studies"
    )
    description = (
        "A scientist-facing research partner spanning research framing, evidence coordination, "
        "simulation, and adversarial review, extended with materials science, manufacturing, "
        "characterization, mechanical testing, fatigue/failure, and data analysis specialists."
    )
    plugins = ScienceAgent.plugins + ["manufacturing", "factorio"]
