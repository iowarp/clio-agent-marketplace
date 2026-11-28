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
scene is saved after every command. Objects have ids (`o1`, `o2`, ...), and the
tools take the id of the object they act on.

## Where ParaView runs

The connector's values decide where ParaView runs: **Where ParaView runs** (an
SSH host name, empty for this machine), **Jump host** and **Command to run
first** (for example a module load line). There is no connect tool.

- `set_connector_value` sets those values (`values` with `address`, `via`,
  `prepare`), for another machine such as "the ParaView on the compute node,
  through the login node". Each call restarts the connector, so values given
  together apply in one restart. Host names are the person's; a guessed one
  reaches the wrong machine or none.
- The first call on a machine prepares a folder there, which can take a
  while; it reports each setup step as progress. Later calls take seconds.
  `setup_stalled` means a setup step printed nothing for a long time and was
  stopped; the error names the step and its last line.
- A call can say no ParaView was found, or that the host wants a password or a
  one-time code. Sign-in is the person's: the connector uses their SSH keys and
  never a password.
- Paths are paths on the machine where ParaView runs, or, when you join a
  `pvserver`, on the machine that `pvserver` runs on.

## Join a pvserver a job serves

A job service can start `pvserver` beside a simulation, in the same cluster
job, and forward its port to this machine. The service's result names that
forwarded endpoint (a `host:port` here, such as `127.0.0.1:<port>`) and the
ParaView version the `pvserver` runs.

- `version` set alone with `set_connector_value` starts the client fetch
  (about a gigabyte). A pvserver package names the version when the job is
  reviewed; set before the job runs, the fetch overlaps the queue and install
  instead of following the service, and a later connector change resumes it
  instead of starting it over.
- The connector attaches with `values` holding `pvserver` (the forwarded
  `host:port`, exactly as the result gives it) and `version` (the server's
  ParaView version, such as `5.13.1`), with `address` and `via` empty. The
  forward already reaches the server, so the connector opens no SSH of its
  own; an `address` on the compute node would.
- `open_view` takes the job's output by its path on the cluster, the one the
  job writes, with `growing` while it is still being written. The data is read
  there; no copy here is needed.
- The first attach on this machine may fetch a matching ParaView client
  (`client_fetching`, with progress) and prepare the connector's folder; the
  connector installs the client itself, and `open_view` succeeds once it is
  there.
- `paraview_version_mismatch` means `version` does not match the version the
  server reports. `node_folder_unwritable` means this host will not let the
  connector write its folder, and names it. An attach that fails the same way
  twice will not pass on a third try; the run does not depend on it (see
  "When the live view could not follow a run" below).
- The endpoint lives only while the job and its forward do. A `pvserver` value
  left set after the job ends still points the connector at it, so opening
  anything on another machine needs it cleared.
- A service can outlive the run it shows: a `pvserver` kept up for review
  (its `linger`) still holds the job's nodes after the run is over
  (`watch_steps` ends `complete` or `finished`, or the run's job ends), until
  the time the job gives, if it gives one. The tool that started it ends it
  (relay's `cancel(operation=...)`), and relay's own confirm is the question
  the person answers; a separate `ask_user` or question in words before it
  asks them twice. "It stops by itself later" leaves the nodes held until
  then. Ending a service is the person's decision, through that confirm.

## Open, then read what is there

`open_view` with the dataset path opens the scene and the view. A glob opens a
file series; mark a series that is still being written as `growing`. The result
lists every object with its fields and their exact ranges, and the time steps;
those are the exact field names the tools take. Passing the `scene` id it returns
to `open_view` reopens exactly that scene.

On a growing source, `open_view` can be called as soon as the run starts. It waits
for the first readable step, reporting progress, and if the source stops changing
before one can be read, it fails with the reason. The run never waits for the
view: it writes its steps as they come, and the view shows the ones already
written when it attaches and follows from there.

## Several views at once

Each scene has a view of its own, side by side, each at its own step and drawn its
own way. To show two variables of one run, open the same path twice with a view
descriptor whose display names each variable (or a `scene` name of your own for
each): each becomes a view, and opening one never moves the others. The other
tools act on the view opened last; `open_view(scene=...)` with a scene id makes
that open view the one they act on.

A view is opened once. Opening a scene that is already open makes no new view:
the result says `already_open` and the person sees the view they already have,
so reopening reads nothing new. `scene_state` lists every open view with its
step, and `scene_state(scene=...)` reads one view without changing which view
the other tools act on. `watch_steps` follows steps as they arrive.

## Look and measure

- `measure_field` gives exact minimum, maximum, mean, median and a histogram.
  An isovalue inside that range gives a surface; a guessed one is often outside
  the data and gives an empty surface.
- `measure_over_time` gives the same exact statistics (minimum, maximum, mean,
  standard deviation, median) of one field at every time step: a quantity
  across all of a run's snapshots, such as how a peak or a mean moves, to plot
  or compare. It measures every object, filters included, at each step's own
  time. On a source still being written it measures every step written so
  far; a later call includes the steps written since. It reports progress per
  step and can be cancelled. `start`, `end` and `stride` pick part of a long
  run; the view stays on its step.
- `capture` renders a PNG at the camera on the person's screen: what the view
  actually shows.
- `inspect_selection` gives the exact values at the point the person picked,
  which is what "what did I pick" asks for.
- What the person does in the view (time step, pick, camera, how objects are
  shown) reaches you as the view's reported context; exact numbers come from
  the tools.
- A value read off a colour bar or an image is approximate; the measure tools
  give exact ones.

## Build the scene with a script

`run_scene_script` runs `paraview.simple` code inside the scene the person sees, so
anything ParaView can do becomes part of it: a second dataset (`OpenDataFile`),
filters, colouring, solid colours, colour ranges, text. The script sees `view` (the
scene's view, the one the person sees: `Show` things in it), `objects` (the
scene's objects by id or label, e.g. `objects["o1"]` for the dataset) and `folder`.

- Each script is one step with a `label` (the cloud shells; the isobars).
- On a growing source the script's filters run again at every new step, early
  ones included, where an array may be empty or not there yet. ParaView's own
  filters (`Calculator`, `Gradient`, `Contour`) handle that; a
  `ProgrammableFilter` that reduces over an input with no points or without the
  array fails at that step.
- Cells built by hand (`vtkCellArray.SetData`, raw offsets and connectivity
  arrays, `InsertNextCell` loops) in a script or a `ProgrammableFilter` are
  fragile: a wrong offset or a freed numpy buffer gives garbage bounds and can
  crash the ParaView server when the view resets its camera. ParaView's own
  sources and filters make geometry without that risk: `Glyph`,
  `ExtractSurface`, `Delaunay2D`, `TableToPoints`, `Line`, `PolyLineSource`,
  `Sphere`. Arrays attached to the input's copy with
  `vtk.numpy_interface.dataset_adapter` (`output.PointData.append(arr, name)`)
  add values to existing points and keep its cells.
- Broken geometry shows in `obj.GetDataInformation().GetBounds()`: a bound that
  is not finite, a min above its max, or values near 1e-308. A script that
  raises leaves nothing behind.
- The view's default colour range is the 2nd to 98th percentile of the shown values. A range set in run_scene_script with `GetColorTransferFunction(f).RescaleTransferFunction(lo, hi)` is kept as set; measure_field on the shown object gives the values. A signed field with a diverging map reads evenly with a symmetric range (±the larger of |p2|, |p98|).
- The result lists what the script made, with the ids to use later. A script that
  fails leaves nothing behind and says why.
- The step is saved with the scene and replayed when the scene is restored, so it
  replays only if its data files stay where they are.
- The person can change what a script made in the view's panel; their edits are
  kept on top of the script.

## Manage the view

- `set_timestep` moves in time or follows the latest step. The person may park
  the view on an earlier step, and moving it takes them off the step they
  chose.
- `watch_steps` reports each new step of a source still being written, as it
  is written, so it follows a run step by step. As a background task, each
  step shows in the task's status; called directly, it reports each step as
  progress and lasts until the watch ends. Progress counts the steps written, against the
  run's expected steps when the view knows them. It ends by itself with the
  run: `complete` (the expected steps are written), `finished` (the writer
  closed its output), `not_growing`, `stalled` (no new step and nothing
  changing on disk for a while) or `cancelled`, and returns every step it
  saw. Then `measure_over_time` gives the series over the whole run.
    `max_seconds` sets a time limit; without it the watch lasts as long as the
    run. The view follows the newest step unless the person parked it.
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
finished output can still be opened in ParaView here once the job ends:

- `open_view` takes the finished output by its path on the machine where
  ParaView runs (the job's run folder, or a copy the job synced), without
  `growing`, since nothing is still being written.
- `set_timestep` reaches the last step, `run_scene_script` builds the display
  the job's outputs suggest (a slice, a contour, a colouring), and `capture`
  shows it.

A live attach after the run has ended has nothing left to follow.

## Keep the result

`export_artifact` writes a figure. `export_animation` writes a video of the time
steps as the view shows them (an MP4, or an OGG where the ParaView machine has no
ffmpeg), with an optional label per step such as its date; one written into the
person's workspace can be shared. A live view only works while ParaView runs; a
dashboard plays the exported animation named as the view's `recordingUri` when
the live view cannot run. `export_scene` writes the scene manifest
and a ParaView state file. `scene_state` says where ParaView is attached, what
the scene holds and which views are open.
