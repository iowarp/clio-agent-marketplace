# EarthScope station-selection surfaces

This catalog covers exactly one workflow: showing a bounded set of ranked GNSS
stations on a map, letting the human pick which ones to analyse, and
delivering that choice back as a structured `earthscope.stations.selected`
event. `StationMap` and `StationPicker` alias the renderer's existing
`clio.map.v1` and `ChoicePicker` kernels (see `catalog.clio.json`); `Text`,
`Column`, `Row`, and `Button` are the unmodified Basic components. Every
property shape is defined in `catalog.json` — this page is about how the
pieces fit, not the field-by-field reference.

## The station-selection surface

- **`StationMap`** (id `stationsMap`) renders the ranked, tool-returned
   points. Its `points` array is a plain literal list — the A2UI wire format
   for `clio.map.v1` does not support a data-model binding for `points` — so
   the points observed from the radius filter (`station_catalog.py within` or
   `geo_filter_points_by_radius`) sit inline on the component. The same points
   mirrored into the data model at `/stations` give later revisions (and the
   picker's options) one place to read them back from without re-deriving them.
- **`StationPicker`** (id `stationsPicker`) is fixed to
   `variant: "multipleSelection"` by this catalog (see `catalog.clio.json`'s
   `presets`) — the catalog's own schema declares `variant` a `const`, so the
   validator refuses any other value. Its `options` are the same ranked
   points as short `{label, value}` pairs (`value` is the exact station id).
   With `value` bound to `/selectedStationIds` — `{"path": "/selectedStationIds"}`
   — the human's picks land in the data model as they are made.
- A **`Button`** (id `confirmButton`) carries a `required` check on the same
   path, so the client refuses to submit with nothing selected:
   ```json
   {
     "condition": {
       "call": "required",
       "args": {"value": {"path": "/selectedStationIds"}},
       "returnType": "boolean"
     },
     "message": "Select at least one station before continuing."
   }
   ```
   Its `action` is a plain agent event; `approval.respond` and `run.*` actions
   route elsewhere:
   ```json
   {
     "event": {
       "name": "earthscope.stations.selected",
       "context": {
         "searchId": {"path": "/searchId"},
         "stationIds": {"path": "/selectedStationIds"}
       }
     }
   }
   ```
   `searchId` is an opaque string chosen when the surface is created (it only
   needs to be stable for this surface's lifetime); `stationIds` resolves to at
   least one id (`context_schema` requires `minItems: 1`) — the check above is
   what keeps that true before the button is even pressable.

## Ids come only from observed evidence

Every id in `/stations`, every `StationMap` point `id`, and every
`StationPicker` option `value` is a station id returned by a tool
(`station_catalog.py within`, `geo_filter_points_by_radius` or the station
catalog search) in this turn. An invented, guessed or carried-over id (from a
different region or a prior unrelated search) points at a station the data does
not support. `searchId` may be any stable opaque string, and `stationIds` in the
delivered event is a subset of the ids rendered.

## One complete example surface

Ranked points observed for one regional search (`searchId: "stations-search-1"`),
with placeholder station ids `STA1`, `STA2`, `STA3`.

`createSurface`:

```json
{
  "version": "v0.9.1",
  "createSurface": {
    "surfaceId": "earthscope-stations",
    "catalogId": "https://iowarp.ai/a2ui/catalogs/earthscope-stations/v1"
  }
}
```

`updateComponents`:

```json
{
  "version": "v0.9.1",
  "updateComponents": {
    "surfaceId": "earthscope-stations",
    "components": [
      {
        "id": "root",
        "component": "Column",
        "children": ["stationsMap", "stationsPicker", "confirmButton"]
      },
      {
        "id": "stationsMap",
        "component": "StationMap",
        "title": "GNSS stations near the resolved region",
        "points": [
          {"id": "STA1", "label": "STA1", "latitude": 34.05, "longitude": -118.25},
          {"id": "STA2", "label": "STA2", "latitude": 34.02, "longitude": -118.41},
          {"id": "STA3", "label": "STA3", "latitude": 33.98, "longitude": -118.30}
        ],
        "selected": "STA1"
      },
      {
        "id": "stationsPicker",
        "component": "StationPicker",
        "variant": "multipleSelection",
        "label": "Select stations to analyse",
        "options": [
          {"label": "STA1", "value": "STA1"},
          {"label": "STA2", "value": "STA2"},
          {"label": "STA3", "value": "STA3"}
        ],
        "value": {"path": "/selectedStationIds"}
      },
      {
        "id": "confirmButton",
        "component": "Button",
        "child": "confirmButtonLabel",
        "variant": "primary",
        "checks": [
          {
            "condition": {
              "call": "required",
              "args": {"value": {"path": "/selectedStationIds"}},
              "returnType": "boolean"
            },
            "message": "Select at least one station before continuing."
          }
        ],
        "action": {
          "event": {
            "name": "earthscope.stations.selected",
            "context": {
              "searchId": {"path": "/searchId"},
              "stationIds": {"path": "/selectedStationIds"}
            }
          }
        }
      },
      {
        "id": "confirmButtonLabel",
        "component": "Text",
        "text": "Analyse selected stations"
      }
    ]
  }
}
```

`updateDataModel`:

```json
{
  "version": "v0.9.1",
  "updateDataModel": {
    "surfaceId": "earthscope-stations",
    "path": "/",
    "value": {
      "searchId": "stations-search-1",
      "stations": [
        {"id": "STA1", "label": "STA1", "latitude": 34.05, "longitude": -118.25},
        {"id": "STA2", "label": "STA2", "latitude": 34.02, "longitude": -118.41},
        {"id": "STA3", "label": "STA3", "latitude": 33.98, "longitude": -118.30}
      ],
      "selectedStationIds": ["STA1"]
    }
  }
}
```

When the human selects `STA1` and `STA2` and presses the button, the
delivered `earthscope.stations.selected` event context is:

```json
{"searchId": "stations-search-1", "stationIds": ["STA1", "STA2"]}
```

## After creating the surface

The surface is the question. Once it is `rendered=true` and `state=ready`,
the human's `earthscope.stations.selected` event arrives either as a new
turn (when the turn ends) or as the answer to a paused question (when paused
with `ask_user(..., surface_id="earthscope-stations")`) — both work. That event
arrives with its meaning already attached (`catalog.clio.json`'s `narration`,
stating that the person picked these stations and wants their time series
staged, profiled, and carried into whatever they originally asked), so the bare
event name and context do not need interpreting as a request to act rather than
a passive report. A pause suits a request to ask or check with the person, or
more work in the same turn once the choice is known (staging, then plotting) —
the selection resumes exactly where it paused. Ending the turn with the surface
ready suits the case where presenting the candidates is the natural end of what
was asked. A station series searched for or staged before the structured
selection arrives may be one the person does not pick.