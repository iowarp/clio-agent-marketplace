---
name: edit-model-grid
title: Edit a Model Grid
description: Review and hand-edit a regional model's 2-D input grid (bathymetry, land mask, topography, land use) with the person, as a replayable edit log; open it in the grid editor, propose edits with reasons, and replay them onto a regenerated grid.
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
you find candidates, propose edits with reasons, and keep the log.

1. **Open it.** `grid_open` with the file (and the variable when the file
   has several 2-D ones). It shows the grid in the editor and returns its
   shape, extent, value range and content hash. Say which convention the
   values follow (depth positive down, elevation negative in the sea, a 0/1
   mask): read the variable's attributes rather than assume it.
2. **Find candidates.** Use the model's own checks first (for a regional
   ocean model, the server's preflight). Otherwise look for isolated wet
   cells, one-cell channels and depths below the model's minimum with a
   short script. List each candidate with its longitude and latitude.
3. **Propose, then edit.** Name each edit and why. Apply them with
   `grid_edit` as one ordered list, each with a `note`; the person can edit
   further in the view, and every change there is a `grid_edit` call too.
   The base file is never changed; the result and its log
   (`<output>.edits.json`) are written beside it.
4. **Keep what the person decided.** When the person keeps a feature you
   flagged (a narrow channel that is real), record it and do not flag it
   again.
5. **Replay.** When the grid is regenerated, `grid_replay` the log onto it.
   Report whether the base is the logged one and every edit that changed a
   different number of cells; check those with the person before the run.

Cite the log's base and result hashes wherever the edited grid is used.
