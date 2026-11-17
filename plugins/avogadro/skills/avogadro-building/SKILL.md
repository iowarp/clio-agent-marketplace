---
name: avogadro-building
title: Building structures in Avogadro
description: Use when the person wants to build or remodel a structure in 3D by hand - assemble it from fragments, change elements, add or remove atoms, drag atoms while it re-optimizes, build a crystal, surface, slab or supercell - or to pick atoms in Avogadro and hand the result to the agent.
keywords: [avogadro, build, edit, crystal, surface, selection, level:L2]
---

# Building and remodelling in Avogadro

**Burette or Avogadro.** Burette is the light viewer in the conversation: look, play
trajectories and modes, pick atoms, set a bond, angle or dihedral. Avogadro is the 3D
builder: fragments and templates, element changes, adding and deleting atoms and bonds,
optimizing while dragging, crystals (space groups, supercells, slabs). Use Avogadro when the
change is more than an internal coordinate, and say why.

## Open

`open_in_avogadro(path)` opens a workspace structure file in a tab (or an empty molecule to
build from scratch). The first open starts Avogadro (seconds). If it says `not_installed` or
`display_missing`, use `install-avogadro`.

## The person works, then says so

The person edits in the tab and selects the atoms they mean (Select menu, or the selection
tool); nothing needs to be sent. When they say they are done, or ask about what they built,
call `read_avogadro`: it reads the molecule open in Avogadro now, writes it as XYZ (and
Avogadro's CJSON) in the workspace, and gives the selected atoms as 0-based indices in that
file's order. Continue from that file (inspect it, optimize it); a hand-built structure is
a starting point. (An Avogadro older than 2.1 cannot report its molecule: there the person
chooses **Extensions > CLIO > Send to CLIO** first, and `read_avogadro` reads that.)

Files the person saves from Avogadro's own Save dialog land in the workspace's
`chemistry/avogadro/` folder; they are ordinary files you can open.

## Look

`avogadro_snapshot` gives a picture of Avogadro's 3D view when you need to see what the
person built. Answer questions about the structure from the sent file (distances and angles
computed with `inspect_structure`), not from the picture.

`close_avogadro` stops it; anything not sent or saved is lost, so say so first.
