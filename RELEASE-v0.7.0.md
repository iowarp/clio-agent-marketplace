CLIO Marketplace 0.7.0 ships the default agents and shared capability plugins for
CLIO 0.9.5. Agents load procedures and tools through the native plugin format.

### Choose agents for scientific work

CLIO Data inspects, checks and converts HDF5, netCDF-4, ADIOS2 and Parquet data.
Method, format and program plugins are separate capabilities that agents can
combine, with conversion checks retained alongside their procedures. (#108)

### Delegate and keep the evidence

Shared delegation guidance covers exploration, planning, review and forks.
Deep research retains verified claims, rejected claims and unresolved gaps so a
report can distinguish its evidence from work that still needs checking.
(#111, #113, #114)

### Keep dashboards with the study

Study guidance keeps measurements and entries in the study log, with Views as
dashboards attached by its conversations. Plugins provide records and reusable
procedures rather than declaring a separate dashboard surface. (#113, #114)

## Changed

This release replaces the blueprint-era layout with agent classes and capability
plugins. Retired demo agents leave the default marketplace; the smoke-test
agents remain available in the separate testing marketplace. Review the
[CHANGELOG](https://github.com/iowarp/clio-agent-marketplace/blob/v0.7.0/CHANGELOG.md)
before migrating custom agent definitions.

## Fixed

Topology aliases use the canonical kernel identifiers. (#115)
