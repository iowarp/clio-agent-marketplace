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
the configuration, and the processor layout against the mask table. Each
finding names the file and parameter it comes from. A failed check says what
the run will get wrong, and a run can finish cleanly and still be wrong in
exactly that way: an earlier run that completed does not show a finding is
harmless. Each failed check is the person's to settle: a fix (an edit to a
configuration or input is theirs to accept), or keeping it on purpose with a
known effect on the result. A preflight speaks for the set-up it read: after
adding forcing or tides, extending the dates or changing boundary files, it is a
different set-up that the earlier preflight does not cover.

## Grid edits

Mask or bathymetry findings are edited with `edit-model-grid` (`grid_open`);
the person decides each channel and lake. Every edit is a tool call and the log
replays onto a regenerated grid. The edited grid is a new set-up for the
preflight.

## After a run

- `drift` over a run: domain and level means of kinetic energy,
  temperature and salinity, with an equilibration test. Which segment counts
  as spun up, and why, is a judgement the result depends on.
- `colocate` sets the model against observations (Argo, CTD, gliders) at their
  position, depth and time; bias and RMSE by depth band and region. The
  profiles of both fit `clio.profile-stack.v1` (`overlayField`).