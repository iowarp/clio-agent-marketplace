"""EarthScope: EarthScope's GNSS data on the National Data Platform."""

from .ndp import Ndp


class Earthscope(Ndp):
    """EarthScope organization semantics (L2) on the NDP package and generic geodesy (L1)."""

    id = "earthscope"
    version = "0.7.0"
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
    # ScienceAgent's additions on top of the NDP agent; geo arrives through geodesy.
    plugins = Ndp.plugins + ["scientific-method", "science-log", "earthscope", "geodesy"]
