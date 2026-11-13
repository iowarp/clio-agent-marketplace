---
name: paraview-scenes
title: ParaView scenes
description: Use when the person wants to see, slice, contour, measure or capture 3D scientific data (meshes, volumes, time series) in ParaView, here or on another machine such as a cluster node. Triggers on "open this in ParaView", "show an isosurface", "what did I pick", "connect to the ParaView on <host>".
keywords: [paraview, visualization, isosurface, slice, mesh, volume, time series, level:L2]
---

# ParaView scenes

The ParaView connector gives you a **scene** in a live view the person sees in a
tab: a dataset, the filters built on it, how each is shown, a time step and a
camera. Each scene tool is one command that applies whole or not at all, and the
scene is saved after every command. Objects have ids (`o1`, `o2`, ...); name the
one you mean.

## Where ParaView runs

The connector's values decide where ParaView runs: **Where ParaView runs** (an
SSH host name, empty for this machine), **Jump host** and **Command to run
first** (for example a module load line). There is no connect tool.

- When the person names another machine ("the ParaView on the compute node,
  through the login node"), set those values with `set_connector_value`
  (`address`, `via`, `prepare`), then call the scene tool. Use the host names
  the person gives; do not guess them.
- The first call on a machine prepares a folder there and can take a minute;
  later calls take seconds.
- If a call says no ParaView was found, or that the host wants a password or a
  one-time code, tell the person what it says. Sign-in is the person's: the
  connector uses their SSH keys and never a password.
- Paths are paths on the machine where ParaView runs.

## Open, then read what is there

`open_view` with the dataset path opens the scene and the view. A glob opens a
file series; mark a series that is still being written as `growing`. The result
lists every object with its fields and their exact ranges, and the time steps.
Read field names from it; never guess one. Keep the scene id it returns: passing
`scene` to `open_view` reopens exactly that scene.

## Look and measure before you claim

- `measure_field` gives exact minimum, maximum, mean, median and a histogram.
  Pick an isovalue from it; a guessed one is often outside the data and gives
  an empty surface.
- `capture` renders a PNG at the camera on the person's screen. Look at it
  before you describe what the view shows.
- `inspect_selection` gives the exact values at the point the person picked.
  Answer "what did I pick" from it.
- What the person does in the view (time step, pick, camera, how objects are
  shown) reaches you as the view's reported context. Use it; confirm numbers
  with the tools.
- Never read a value off a colour bar or an image.

## Change the scene

- `create_filter` takes ParaView's filter names and property names, for example
  `Contour` with `ContourBy` and `Isosurfaces`, `Slice`, `Clip`, `Threshold`.
  A wrong property name is refused with the names that exist, and nothing
  changes.
- `set_representation` sets Surface, Wireframe, Points, Outline or Volume, the
  field to colour by, and a colour preset; prefer a perceptually uniform preset
  such as Viridis for continuous data.
- `set_timestep` moves in time or follows the latest step. The person may park
  the view on an earlier step; say when newer steps exist rather than moving
  them.
- `set_camera`, `fit_camera`, `remove_scene_object` do what they say.
- Large geometry is drawn by ParaView and sent as images; the view says so.

## Keep the result

`export_artifact` writes a figure; `export_scene` writes the scene manifest and
a ParaView state file. `scene_state` says where ParaView is attached and what
the scene holds. Report the machine, the source, the time step, the filters, the
field and its association, and the image you captured.
