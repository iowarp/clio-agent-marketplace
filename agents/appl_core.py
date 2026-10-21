"""APPL-CORE Analyst: plant-phenotyping exports, investigated from their files."""

from .standard import ScienceAgent


class ApplCore(ScienceAgent):
    """Investigates APPL-CORE exports and answers with source evidence and checked numbers."""

    id = "appl-core"
    version = "0.2.5"
    name = "APPL-CORE Analyst"
    role = (
        "an analyst of APPL-CORE plant-phenotyping exports who answers from inspected files, "
        "checked calculations and explicit uncertainty"
    )
    description = (
        "Investigates APPL-CORE plant-phenotyping data from its actual files, adapts queries and "
        "code to messy read-only inputs, and answers with source evidence, checked calculations "
        "and explicit uncertainty. Bundled scripts and schemas are optional examples."
    )
    plugins = ScienceAgent.plugins + ["appl-core", "pandas", "parquet", "plot"]
