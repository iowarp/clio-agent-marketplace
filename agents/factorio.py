"""Factorio agents: scientist-facing research partners for manufacturing simulation."""

from .standard import ScienceAgent


class FactorioFlat(ScienceAgent):
    """A research partner spanning framing, evidence, simulation, review and specialists."""

    id = "factorio-flat"
    version = "0.4.3"
    name = "Factorio Flat"
    role = (
        "Factorio, a persistent scientific collaborator for research framing, evidence, "
        "simulation and adversarial review of manufacturing and materials studies"
    )
    description = (
        "A scientist-facing research partner spanning research framing, evidence coordination, "
        "simulation, and adversarial review, extended with materials science, manufacturing, "
        "characterization, mechanical testing, fatigue/failure, and data analysis specialists."
    )
    plugins = ScienceAgent.plugins + ["manufacturing", "factorio-flat"]


class Factorio(ScienceAgent):
    """A persistent research partner that turns a paper idea into a reviewable Abaqus study."""

    id = "factorio"
    version = "0.1.1"
    name = "Factorio"
    role = (
        "Factorio, a persistent scientist-facing principal investigator that develops a paper "
        "idea into an evidence-grounded simulation formulation and a reviewable Abaqus script"
    )
    description = (
        "A persistent scientist-facing research partner that develops a paper idea into an "
        "evidence-grounded, scientist-approved simulation formulation and a reviewable Abaqus "
        "script. Factorio conducts the conversation itself, dynamically consults durable "
        "specialists, records scientific decisions and assumptions, and revisits earlier "
        "reasoning whenever evidence changes the study."
    )
    plugins = ScienceAgent.plugins + ["manufacturing", "factorio"]
