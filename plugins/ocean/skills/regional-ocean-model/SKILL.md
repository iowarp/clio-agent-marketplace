---
name: regional-ocean-model
title: Regional Ocean Model Checks
description: Check a regional ocean model set-up before it runs (MOM6 open boundaries, dates, mask, minimum depth, processor layout), edit its grids with the person, and evaluate runs for drift and against observations.
keywords:
- level:L1
- ocean
- model
- mom6
---

# Regional ocean model checks

## Before a run

`mom6_preflight` reads the configuration and input files and checks what
is usually got wrong by hand: open boundaries against the segment files,
boundary and initial-condition dates against the run, isolated wet cells
and one-cell channels in the mask, minimum depth in the bathymetry against
the configuration, and the processor layout against the mask table. Report
every finding with the file and parameter it comes from. A preflight speaks
for the set-up it read: after adding forcing or tides, extending the dates or
changing boundary files, it is a different set-up, so check it again before
running it.

## Grid edits

For mask or bathymetry findings, open the grid with `edit-model-grid`
(`grid_open`) and propose edits; the person decides each channel and lake.
Every edit is a tool call and the log replays onto a regenerated grid.
Rerun the preflight on the edited grid.

## After a run

- `drift` over a run: domain and level means of kinetic energy,
  temperature and salinity, with an equilibration test. Say which segment
  you call spun up and why.
- `colocate` the model with observations (Argo, CTD, gliders) at their
  position, depth and time; bias and RMSE by depth band and region. Show
  the profiles of both with `clio.profile-stack.v1` (`overlayField`).
