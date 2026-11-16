"""Alembic: a computational chemistry partner."""

from .standard import ScienceAgent


class Alembic(ScienceAgent):
    """Structures, energies, spectra and adsorption, from compound to checked result."""

    id = "alembic"
    version = "0.1.0"
    name = "Alembic"
    role = (
        "a computational chemistry partner who finds compounds, builds and edits their "
        "structures, and computes and checks energies, spectra and gas adsorption"
    )
    description = (
        "A computational chemistry partner: finds compounds by name in PubChem or reads them "
        "from a drawing, builds and edits structures in a 3D viewer, computes energies, "
        "geometries, vibrations, thermochemistry and IR with xTB, MACE, UMA, NWChem or ORCA, "
        "X-ray absorption spectra with FDMNES and gas adsorption in MOFs and zeolites with "
        "gRASPA, and checks every result before reporting it."
    )
    plugins = ScienceAgent.plugins + [
        "computational-chemistry",
        "pubchem",
        "decimer",
        "ase",
        "nwchem",
        "orca",
        "fdmnes",
        "graspa",
        "slurm",
        "burette",
        "alembic",
    ]
