"""EarthScope: GNSS station data from EarthScope, found through the National Data Platform."""

from .standard import ScienceAgent


class Earthscope(ScienceAgent):
    """EarthScope GNSS via NDP (L2 source) on the generic geodesy methods (L1)."""

    id = "earthscope"
    version = "0.6.0"
    name = "EarthScope"
    role = (
        "a geodesist who analyses EarthScope GNSS station data found through the National Data "
        "Platform"
    )
    description = (
        "Finds and stages EarthScope GNSS station catalogs and position time series through the "
        "National Data Platform, lets you pick stations on a map, and analyses them with GNSS "
        "methods: velocities, offsets, seasonal terms and honest rate uncertainty, plus station "
        "coverage across regions."
    )
    plugins = ScienceAgent.plugins + ["earthscope", "geodesy", "geo", "ndp"]
