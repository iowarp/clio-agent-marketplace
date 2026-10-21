"""Seismic Waveform Review Agent (archived): one plugin and its subagents."""

from clio_agent.sdk import Agent


class SeismicWaveformReview(Agent):
    """Discovers bounded seismic waveform data, inspects SAC traces, and prepares plot-ready evidence."""

    id = "seismic-waveform-review"
    version = "0.1.0"
    name = "Seismic Waveform Review Agent"
    role = "a seismic waveform reviewer that finds bounded waveform data, inspects SAC traces and prepares plot-ready evidence"
    description = "Discovers bounded seismic waveform data, inspects SAC traces, and prepares plot-ready evidence."
    plugins = Agent.plugins + ["seismic-waveform-review", "delegation"]
