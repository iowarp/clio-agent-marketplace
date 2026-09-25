# Producing topology optimization surfaces

This catalog has two views of a topology optimization run, built from the
same generic parts. `TopologyViewport` aliases the renderer's
`clio.mesh-viewport.v1` kernel, `DesignMetric` aliases `clio.metric.v1`,
and `ConvergencePlot` aliases `clio.time-series.v1` (see
`catalog.clio.json`); `Text`, `ParameterSlider` aliases `clio.slider.v1` (a slider with a step, a unit,
and a box to type an exact value); `Text`, `Column`, `Row`, `Button`, and
`CheckBox` are the unmodified Basic components. Property shapes live in
`catalog.json`; this page is the recipe. Load the `abaqus-visualization`
and `visualize-topology-optimization` skills for how the meshes are made.

Every `meshUri` is an artifact registered in this session from the
exporter's output. Never an inline mesh, never a filesystem path. Every
number on a surface comes from the exporter's printed metadata or Tosca's
report files, never estimated.

## View 1: before and after, with a stress toggle

Two `TopologyViewport`s in a `Row`, one per design state, with the same
`syncGroup` so they orbit together and share one stress color scale. A
shared scale is what makes the comparison honest: two independently scaled
contour plots always look equally "red". Both use `field: "S_MISES"` with
`showField` bound to `/showStress`, and one `CheckBox` bound to the same
path is the toggle; start it at `false` so the first thing the scientist
sees is the shape change. `DesignMetric`s show retained volume and peak
nodal von Mises (label it nodal, since Tosca evaluates its stress constraint
differently), and two `Button`s send `abaqus.topology.reviewed` with
`decision` `accept` or `revise`.

`createSurface`:

```json
{
  "version": "v0.9.1",
  "createSurface": {
    "surfaceId": "topology-compare",
    "catalogId": "https://iowarp.ai/a2ui/catalogs/abaqus-topology/v1"
  }
}
```

`updateComponents`:

```json
{
  "version": "v0.9.1",
  "updateComponents": {
    "surfaceId": "topology-compare",
    "components": [
      {"id": "root", "component": "Column", "children": ["heading", "views", "stressToggle", "metrics", "actions"]},
      {"id": "heading", "component": "Text", "variant": "h3", "text": "IN718 specimen: stress-constrained volume minimization"},
      {"id": "views", "component": "Row", "children": ["beforeView", "afterView"]},
      {
        "id": "beforeView",
        "component": "TopologyViewport",
        "title": "Before optimization",
        "meshUri": "artifact://artifact_exp10base",
        "field": "S_MISES",
        "showField": {"path": "/showStress"},
        "syncGroup": "run-exp10-prod",
        "upAxis": "y",
        "weight": 1
      },
      {
        "id": "afterView",
        "component": "TopologyViewport",
        "title": "After optimization",
        "meshUri": "artifact://artifact_exp10opt",
        "field": "S_MISES",
        "showField": {"path": "/showStress"},
        "syncGroup": "run-exp10-prod",
        "upAxis": "y",
        "weight": 1
      },
      {"id": "stressToggle", "component": "CheckBox", "label": "Show von Mises stress", "value": {"path": "/showStress"}},
      {"id": "metrics", "component": "Row", "children": ["volumeMetric", "peakBefore", "peakAfter"]},
      {"id": "volumeMetric", "component": "DesignMetric", "label": "Design volume retained", "value": {"path": "/metrics/volumeRetainedPct"}, "unit": "%"},
      {"id": "peakBefore", "component": "DesignMetric", "label": "Peak nodal von Mises, before", "value": {"path": "/metrics/peakBefore"}, "unit": "MPa"},
      {"id": "peakAfter", "component": "DesignMetric", "label": "Peak nodal von Mises, after", "value": {"path": "/metrics/peakAfter"}, "unit": "MPa"},
      {"id": "actions", "component": "Row", "children": ["acceptButton", "reviseButton"]},
      {
        "id": "acceptButton",
        "component": "Button",
        "child": "acceptLabel",
        "variant": "primary",
        "action": {"event": {"name": "abaqus.topology.reviewed", "context": {"runId": {"path": "/runId"}, "decision": "accept"}}}
      },
      {"id": "acceptLabel", "component": "Text", "text": "Accept design"},
      {
        "id": "reviseButton",
        "component": "Button",
        "child": "reviseLabel",
        "action": {"event": {"name": "abaqus.topology.reviewed", "context": {"runId": {"path": "/runId"}, "decision": "revise"}}}
      },
      {"id": "reviseLabel", "component": "Text", "text": "Revise formulation"}
    ]
  }
}
```

`updateDataModel`:

```json
{
  "version": "v0.9.1",
  "updateDataModel": {
    "surfaceId": "topology-compare",
    "path": "/",
    "value": {
      "runId": "exp10-prod",
      "showStress": false,
      "metrics": {"volumeRetainedPct": 44.6, "peakBefore": 169.4, "peakAfter": 170.5}
    }
  }
}
```

Pressing "Accept design" delivers:

```json
{"runId": "exp10-prod", "decision": "accept"}
```

## View 2: design history, with density and cycle sliders

One `TopologyViewport` on the design-history mesh: the `--cells --frames all`
export of the combined optimization ODB, which carries every element face
and the Tosca `DENSITY` of every cycle. Color by `DENSITY`, threshold by
`DENSITY` from `/iso` up to `1`, and bind `frame` to `/cycle`. Two
`ParameterSlider`s drive those paths; the scientist can drag them or type an
exact value:

- **Density threshold** (`/iso`, `min: 0`, `max: 1`, `step: 0.01`): moving
  it removes elements below the level, which is what Tosca's iso surface
  does. Start it at the `.par` file's `ISO_VALUE`. A load path that breaks as
  the threshold rises is a finding to report.
- **Design cycle** (`/cycle`, `min: 0`, `max` = number of exported frames
  minus 1, `step: 1`): steps the density field through the cycles. Start it
  at the last cycle.

Hovering shows the density of the element under the cursor. Beside the
view, a `ConvergencePlot` shows `optimization_report.csv` per cycle as inline
`series` (one row per cycle). Plot each quantity divided by the report's
`Norm-Values` row, as Tosca's own report does: volume against the starting
volume and peak stress against the stress limit put both near 1, where one
axis can show them. Raw volume and stress differ by orders of magnitude and
flatten each other. Bind the
viewport's `camera` to `/camera`; the viewport keeps the current view there,
so the "Use this view in the report" `Button` can send the camera, cycle,
and threshold in `abaqus.topology.figure-requested`, and you render the
same figure with `render_view.py`.

`createSurface`:

```json
{
  "version": "v0.9.1",
  "createSurface": {
    "surfaceId": "topology-history",
    "catalogId": "https://iowarp.ai/a2ui/catalogs/abaqus-topology/v1"
  }
}
```

`updateComponents`:

```json
{
  "version": "v0.9.1",
  "updateComponents": {
    "surfaceId": "topology-history",
    "components": [
      {"id": "root", "component": "Column", "children": ["heading", "body", "figureButton"]},
      {"id": "heading", "component": "Text", "variant": "h3", "text": "How the design formed"},
      {"id": "body", "component": "Row", "children": ["designView", "side"]},
      {
        "id": "designView",
        "component": "TopologyViewport",
        "title": "Design density",
        "meshUri": "artifact://artifact_exp10design",
        "field": "DENSITY",
        "frame": {"path": "/cycle"},
        "thresholdField": "DENSITY",
        "thresholdMin": {"path": "/iso"},
        "thresholdMax": 1,
        "camera": {"path": "/camera"},
        "upAxis": "y",
        "weight": 3
      },
      {"id": "side", "component": "Column", "children": ["isoSlider", "cycleSlider", "convergence"], "weight": 2},
      {"id": "isoSlider", "component": "ParameterSlider", "label": "Density threshold", "min": 0, "max": 1, "step": 0.01, "value": {"path": "/iso"}},
      {"id": "cycleSlider", "component": "ParameterSlider", "label": "Design cycle", "min": 0, "max": 20, "step": 1, "value": {"path": "/cycle"}},
      {
        "id": "convergence",
        "component": "ConvergencePlot",
        "title": "Volume and peak stress, relative to start and limit",
        "xKey": "cycle",
        "yKeys": ["volumeRatio", "stressRatio"],
        "series": [
          {"cycle": 0, "volumeRatio": 1.0, "stressRatio": 1.672},
          {"cycle": 1, "volumeRatio": 1.017, "stressRatio": 1.024},
          {"cycle": 2, "volumeRatio": 0.988, "stressRatio": 0.887},
          {"cycle": 3, "volumeRatio": 0.961, "stressRatio": 0.970},
          {"cycle": 4, "volumeRatio": 0.928, "stressRatio": 0.917}
        ]
      },
      {
        "id": "figureButton",
        "component": "Button",
        "child": "figureLabel",
        "action": {
          "event": {
            "name": "abaqus.topology.figure-requested",
            "context": {"runId": {"path": "/runId"}, "camera": {"path": "/camera"}, "frame": {"path": "/cycle"}, "iso": {"path": "/iso"}}
          }
        }
      },
      {"id": "figureLabel", "component": "Text", "text": "Use this view in the report"}
    ]
  }
}
```

`updateDataModel`:

```json
{
  "version": "v0.9.1",
  "updateDataModel": {
    "surfaceId": "topology-history",
    "path": "/",
    "value": {"runId": "exp10-prod", "iso": 0.51, "cycle": 20}
  }
}
```

After the scientist orbits to an angle, sets the threshold to 0.45 at the
last cycle, and presses the button, the delivered context is:

```json
{"runId": "exp10-prod", "camera": {"position": [92.1, 131.4, 88.0], "target": [0.0, 73.1, 12.5], "up": [0, 1, 0], "fov": 35, "zoom": 1}, "frame": 20, "iso": 0.45}
```

Render it with the same numbers through `abaqus-visualization`'s
`render_view.py` (`design.glb -o figure.png --field DENSITY --frame 20
--threshold DENSITY:0.45:1 --camera 'CAMERA_JSON'`), register the PNG, and
cite it.

## After creating a surface

The surface is the review. End the turn with it ready when showing the
result is what was asked; pause with `ask_user(..., surface_id=...)` when
you have more to do once the scientist acts. Both events arrive with their
meaning attached (`narration` in `catalog.clio.json`). Reuse the same
surface id after a rerun so the view updates in place.
