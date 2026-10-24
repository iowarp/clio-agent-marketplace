"""Factorio: a research partner for manufacturing and materials science."""

from .standard import ScienceAgent


class Factorio(ScienceAgent):
    """Design, material and manufacturing route to performance, with specialists and programs."""

    id = "factorio"
    version = "0.6.0"
    name = "Factorio"
    role = (
        "a research partner for manufacturing and materials science: how a part's design, "
        "material and manufacturing route set its performance"
    )
    description = (
        "A research partner for scientists who study how a part's design, material and "
        "manufacturing route set its performance: research framing, evidence, simulation and "
        "topology optimization in Abaqus or Morphorm, additive and conventional manufacturing, "
        "characterization, mechanical testing, and fatigue and failure, with specialists for "
        "each and batch runs on Slurm clusters."
    )
    plugins = ScienceAgent.plugins + ["manufacturing", "abaqus", "morphorm", "slurm", "factorio"]
