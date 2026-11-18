---
name: climate-evaluation
title: Climate Model Evaluation
description: Evaluate a climate or regional model run against reanalysis, compute climate indices and composites by phase, and summarise CMIP6 projections per model with their spread.
keywords:
- level:L1
- climate
- evaluation
- cmip6
- enso
---

# Climate model evaluation

## A run against reanalysis

`evaluate_run` puts the run and the reference on a common grid and returns
bias maps, zonal means and seasonal cycles per region. Use the same period
in both, say which reference and which regridding, and show the bias map
on the layered map, the zonal mean as a section, and the seasonal cycles as
a chart per region.

## Indices and composites

`climate_index` computes an index from a field by a stated definition (for
example an SST box average for ENSO, a pressure pattern for the NAO) and
classifies years into phases by a stated threshold. `composite` averages a
field over each phase's years. Report the definition, the baseline, the
threshold and the number of years per phase; a composite of few years is
weak, so say so.

## CMIP6 projections

`cmip_change` reads the Pangeo CMIP6 catalog and returns the regional change
per model between two periods under a scenario. Show each model, the
multi-model mean and the spread; one model per institution unless the
person asks otherwise, and say which members you used. Disagreement between
models is a result, not noise to average away.
