---
name: edit-model-grid
title: Edit a Model Grid
description: Reviewing and hand-editing a regional model's 2-D input grid (bathymetry, land mask, topography, land use) with the person as a replayable edit log - the grid editor, edits with reasons, and replay onto a regenerated grid.
keywords:
- level:L0
- grid
- model
- bathymetry
---

# Edit a model grid

A generated grid often needs edits by hand before a model runs on it: a
channel the model cannot resolve, a strait that must stay open, a minimum
depth, wet cells cut off from the open water. The person decides these;
candidates, proposed edits with reasons and the log are what the agent brings.

- **Opening.** `grid_open` takes the file (and the variable when the file
  has several 2-D ones). It shows the grid in the editor and returns its
  shape, extent, value range and content hash. The values follow a
  convention (depth positive down, elevation negative in the sea, a 0/1
  mask) that the variable's attributes state; assuming one can invert edits.
- **Candidates.** The model's own checks are the most direct (for a regional
  ocean model, the server's preflight). A short script finds isolated wet
  cells, one-cell channels and depths below the model's minimum. Longitude and
  latitude let the person find each candidate.
- **Edits.** Each edit has a reason. `grid_edit` applies them as one ordered
  list, each with a `note`; the person can edit
  further in the view, and every change there is a `grid_edit` call too.
  The base file is never changed; the result and its log
  (`<output>.edits.json`) are written beside it.
- **The person's decisions.** A feature the person keeps (a narrow channel
  that is real) is a decision; flagging it again repeats a settled question.
- **Replay.** `grid_replay` applies the log to a regenerated grid. It shows
  whether the base is the logged one and which edits changed a different number
  of cells; those are the ones that may no longer mean what the person decided.

The log's base and result hashes identify the edited grid wherever it is used.
