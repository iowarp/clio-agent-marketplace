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
- The first call on a machine prepares a folder there, which can take a
  while; it reports each setup step as progress, so wait for it. Later calls
  take seconds. `setup_stalled` means a setup step printed nothing for a long
  time and was stopped; tell the person the step and its last line, which the
  error names.
- If a call says no ParaView was found, or that the host wants a password or a
  one-time code, tell the person what it says. Sign-in is the person's: the
  connector uses their SSH keys and never a password.
- Paths are paths on the machine where ParaView runs, or, when you join a
  `pvserver`, on the machine that `pvserver` runs on.

## Join a pvserver a job serves

A job service can start `pvserver` beside a simulation, in the same cluster
job, and forward its port to this machine. The service's result names that
forwarded endpoint (a `host:port` here, such as `127.0.0.1:<port>`) and the
ParaView version the `pvserver` runs. To show the run live:

- Make one `set_connector_value` call with `values` holding `pvserver` (the
  forwarded `host:port`, exactly as the result gives it) and `version` (the
  server's ParaView version, such as `5.13.1`), and `address` and `via` empty.
  The forward already reaches the server, so the connector opens no SSH of its
  own; do not point `address` at the compute node.
- Then `open_view` the job's output by its path on the cluster, the one the
  job writes, with `growing` while it is still being written. The data is read
  there, so do not copy it here.
- The first attach on this machine may fetch a matching ParaView client
  (`client_fetching`, with progress) and prepare the connector's folder. Wait
  and call `open_view` again; do not install anything yourself.
- `paraview_version_mismatch` means `version` does not match the server; set
  the version the server reports. `node_folder_unwritable` means this host
  will not let the connector write its folder; tell the person what it names.
  An attach that fails the same way twice will not pass on a third try: say
  why, keep the run going, and follow "When the live view could not follow a
  run" below.
- The endpoint lives only while the job and its forward do. When the job ends,
  clear `pvserver` before you open anything on another machine.
- A service can outlive the run it shows: a `pvserver` kept up for review
  (its `linger`) still holds the job's nodes. As soon as the run is over
  (`watch_steps` ends `complete` or `finished`, or the run's job ends) and the
  service still runs, say in that same reply that it still holds the job's
  nodes, and until when if the job says, and offer to end it now by calling
  the tool that started it (relay's `cancel(operation=...)`). Relay's own
  confirm is the question the person answers, so do not ask first with
  `ask_user` or in words: that asks them twice. "It stops by itself later" is
  not the offer. Never end a service without that confirm.

## Open, then read what is there

`open_view` with the dataset path opens the scene and the view. A glob opens a
file series; mark a series that is still being written as `growing`. The result
lists every object with its fields and their exact ranges, and the time steps.
Read field names from it; never guess one. Keep the scene id it returns: passing
`scene` to `open_view` reopens exactly that scene.

On a growing source, call `open_view` as soon as the run starts. It waits for the
first readable step, reporting progress, and if the source stops changing before
one can be read, it fails with the reason; tell the person that reason.

## Several views at once

Each scene has a view of its own, side by side, each at its own step and drawn its
own way. To show two variables of one run, open the same path twice with a view
descriptor whose display names each variable (or a `scene` name of your own for
each): each becomes a view, and opening one never moves the others. The other
tools act on the view you opened last; to act on another open view, call
`open_view(scene=...)` with its scene id first.

A view is opened once. Opening a scene that is already open makes no new view:
the result says `already_open` and the person sees the view they already have.
Never call `open_view` to read a view's step or state, in a loop or otherwise:
`scene_state` lists every open view with its step, and `scene_state(scene=...)`
reads one view without changing which view the other tools act on. To follow
steps as they arrive, use `watch_steps`.

## Look and measure before you claim

- `measure_field` gives exact minimum, maximum, mean, median and a histogram.
  Pick an isovalue from it; a guessed one is often outside the data and gives
  an empty surface.
- `measure_over_time` gives the same exact statistics (minimum, maximum, mean,
  standard deviation, median) of one field at every time step: use it for a
  quantity across all of a run's snapshots, such as how a peak or a mean moves,
  to plot or compare. It measures every object, filters included, at each
  step's own time. On a source still being written it measures every step
  written so far, so call it while the run goes and again as new steps arrive.
  It reports progress per step and can be cancelled. `start`, `end` and
  `stride` pick part of a long run; the view stays on its step.
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
- On a growing source the script's filters run again at every new step, early
  ones included, where an array may be empty or not there yet. Prefer ParaView's
  own filters (`Calculator`, `Gradient`, `Contour`) to a `ProgrammableFilter`. In
  a `ProgrammableFilter`, return before any reduction when the input has no
  points or lacks the array.
- The view's default colour range is the 2nd to 98th percentile of the shown values. If a feature still reads faint, measure the field (measure_field on the shown object) and set the range in run_scene_script with `GetColorTransferFunction(f).RescaleTransferFunction(lo, hi)` (kept as set). For a signed field with a diverging map, set a symmetric range (±the larger of |p2|, |p98|).
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
- `watch_steps` reports each new step of a source still being written, as it
  is written: use it to follow a run step by step and say how far it has got.
  Start it as a background task when the run begins and read each step from
  the task's status; called directly, it reports each step as progress and
  lasts until the watch ends. Progress counts the steps written, against the
  run's expected steps when the view knows them. It ends by itself with the
  run: `complete` (the expected steps are written), `finished` (the writer
  closed its output), `not_growing`, `stalled` (no new step and nothing
  changing on disk for a while) or `cancelled`, and returns every step it
  saw. Then `measure_over_time` gives the series over the whole run. Give
  `max_seconds` only when the person asks for a time limit. The view follows
  the newest step unless the person parked it.
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
and a ParaView state file. `scene_state` says where ParaView is attached, what
the scene holds and which views are open. Report the machine, the source, the time step, the filters, the
field and its association, and the image you captured.
