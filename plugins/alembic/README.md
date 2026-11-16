# alembic

Alembic's own plugin: its mission fragment and the study skills `structure-from-name`, `molecule-properties`, `reaction-study`, `adsorption-screen` and `xanes-comparison`. The agent
(`agents/alembic.py`) composes it with the L1 `computational-chemistry` method plugin and
the L2 program plugins: `pubchem`, `decimer`, `ase`, `nwchem`, `orca`, `fdmnes`, `graspa`
(with `slurm` for GPU nodes) and `burette`. The ase, fdmnes, graspa and burette plugins
follow their connectors; pubchem and decimer follow clio-kit's servers of the same name.

Level: L1 domain (computational chemistry), L2 programs. Docking is deferred
(clio-agent `docs/design/chemistry-in-clio-deferred.md`).
