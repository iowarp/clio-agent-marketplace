"""HPC I/O Regression Agent (archived): one plugin and its subagents."""

from clio_agent.sdk import Agent


class HpcIoRegression(Agent):
    """Compares HPC I/O traces across two application versions and attributes performance regressions."""

    id = "hpc-io-regression"
    version = "0.1.0"
    name = "HPC I/O Regression Agent"
    role = "an HPC I/O regression analyst that compares traces across two application versions"
    description = "Compares HPC I/O traces across two application versions and attributes performance regressions."
    plugins = Agent.plugins + ["hpc-io-regression", "delegation"]
