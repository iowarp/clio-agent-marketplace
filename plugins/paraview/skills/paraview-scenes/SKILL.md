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
  through the login node"), set those values with one `set_connector_value`
  call (`values` with `address`, `via`, `prepare`), then call the scene tool.
  Each call restarts the connector, so give the values together. Use the host names
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

## Build the scene with a script

`run_scene_script` runs `paraview.simple` code inside the scene the person sees, so
anything ParaView can do becomes part of it: a second dataset (`OpenDataFile`),
filters, colouring, solid colours, colour ranges, text. The script sees `view` (the
scene's view: `Show` things in it, never create another), `objects` (the scene's
objects by id or label, e.g. `objects["o1"]` for the dataset) and `folder`.

- One step builds one idea (the cloud shells; the isobars) and gets a `label`.
- Read field names and ranges from the scene first, and choose values from
  `measure_field`, not guesses.
- The result lists what the script made, with the ids to use later. A script that
  fails leaves nothing behind and says why; fix it and run it again.
- The step is saved with the scene and replayed when the scene is restored, so the
  script must read its data from files that stay where they are.
- The person can change what a script made in the view's panel; their edits are
  kept on top of the script.

## Manage the view

- `set_timestep` moves in time or follows the latest step. The person may park
  the view on an earlier step; say when newer steps exist rather than moving
  them.
- `set_camera` and `fit_camera` place the camera.
- Large geometry, volumes and image slices are drawn by ParaView and sent as
  images; the view says so.

## In a dashboard

The live view can sit in a dashboard beside charts: a `clio.mcp-app.v1` component
with server `paraview`, tool `open_view` and the `scene` the view already has, so
the dashboard shows that scene rather than a picture of it. The view reports its
time step as `time` (with `time_index`), and `set_timestep` takes `time`, so the
state channel `{key: "time", path: "/selection/time", tool: "set_timestep"}` links
it to a chart that selects on the same path, both ways.

## When the live view could not follow a run

A simulation or other job can name an output to watch while it runs. If the
live view could not attach while it ran (the connector could not reach the
machine, the job never published where to join, or the attach failed), the
result still deserves a look. When the job ends, say that its output is
complete and offer once to open it in ParaView here. Once the person accepts:

- `open_view` the finished output by its path on the machine where ParaView
  runs (the job's run folder, or a copy the job synced), without `growing`,
  since nothing is still being written.
- `set_timestep` to the last step, build the display the job's outputs
  suggest (a slice, a contour, a colouring) with `run_scene_script`, then
  `capture` and describe what the view shows.

If they decline, say where the output is so they can open it later. Do not
retry the live attach after the run has ended.

## Keep the result

`export_artifact` writes a figure. `export_animation` writes a video of the time
steps as the view shows them (an MP4, or an OGG where the ParaView machine has no
ffmpeg), with an optional label per step such as its date; write it into the
person's workspace to share it. A live view only works while ParaView runs, so a
dashboard that shows one should name its exported animation as the view's
`recordingUri`; the dashboard plays it when the live view cannot run. `export_scene` writes the scene manifest
and a ParaView state file. `scene_state` says where ParaView is attached and what
the scene holds. Report the machine, the source, the time step, the filters, the
field and its association, and the image you captured.
