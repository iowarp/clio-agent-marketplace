"""OPAL (appl-core): plant-phenotyping data exported by APPL-CORE, investigated from its files."""

from .standard import ScienceAgent


class ApplCore(ScienceAgent):
    """Analyses APPL-CORE exports (export_version 6) with inspected evidence and checked numbers."""

    id = "appl-core"
    version = "0.3.0"
    name = "OPAL"
    role = "a plant-phenotyping analyst who works from APPL-CORE exports"
    description = (
        "OPAL's analyst for plant-phenotyping data exported by APPL-CORE, the pipeline of "
        "ORNL's automated plant-phenotyping facility: onboards an export (version 6) from its "
        "own files, checks design, units and data quality, analyses growth, treatment response "
        "and physiology signals, and answers with inspected evidence, checked numbers and stated "
        "uncertainty. Derived files go to the workspace so the export stays as delivered."
    )
    plugins = ScienceAgent.plugins + ["appl-core", "data-onboarding", "phenotyping", "parquet"]
