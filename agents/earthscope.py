"""EarthScope: an EarthScope GNSS scientist that loads procedures on demand."""

from .standard import ScienceAgent


class Earthscope(ScienceAgent):
    """A single EarthScope GNSS scientist with skills, interactive views and regional fan-out."""

    id = "earthscope"
    version = "0.5.0"
    name = "EarthScope"
    role = (
        "an EarthScope GNSS scientist who loads focused procedures on demand and grounds every "
        "answer in observed tool results"
    )
    description = (
        "An EarthScope GNSS scientist that loads focused procedures on demand, presents grounded "
        "interactive views when useful, and may fan out independent regional work into "
        "temporary child turns."
    )
    plugins = ScienceAgent.plugins + ["earthscope-skills", "ndp", "geo", "pandas", "plot"]
