# Producing EarthScope station-selection surfaces

This catalog covers exactly one workflow: showing a bounded set of ranked GNSS
stations on a map, letting the human pick which ones to analyse, and
delivering that choice back as a structured `earthscope.stations.selected`
event. `StationMap` and `StationPicker` alias the renderer's existing
`clio.map.v1` and `ChoicePicker` kernels (see `catalog.clio.json`); `Text`,
`Column`, `Row`, and `Button` are the unmodified Basic components. Every
property shape is defined in `catalog.json` — this page is about the
recipe, not the field-by-field reference.

This catalog's id is `https://iowarp.ai/a2ui/catalogs/earthscope-stations/v1`.
A station surface is created against it by name: pass that id as
`create_a2ui_surface`'s `catalog_id` (a surface created with an empty
`catalog_id` uses the agent's default catalog, which is not this one).

## The station-selection recipe

1. **`StationMap`** (id `stationsMap`) renders the ranked, tool-returned
   points. Its `points` array is a plain literal list — the A2UI wire format
   for `clio.map.v1` does not support a data-model binding for `points` — so
   inline the exact points you just observed from `geo_filter_points_by_radius`
   directly on the component. Also mirror the same points into the data model
   at `/stations` so later revisions (and the picker's options) have one
   place to read them back from without re-deriving them.
2. **`StationPicker`** (id `stationsPicker`) is fixed to
   `variant: "multipleSelection"` by this catalog (see `catalog.clio.json`'s
   `presets`) — the catalog's own schema declares `variant` a `const`, so the
   validator refuses any other value. Its `options` are the same ranked
   points as short `{label, value}` pairs (`value` is the exact station id).
   Bind `value` to `/selectedStationIds` — `{"path": "/selectedStationIds"}`
   — so the human's picks land in the data model as they are made.
3. A **`Button`** (id `confirmButton`) carries a `required` check on the same
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
   Its `action` is a plain agent event — never `approval.respond` or a
   `run.*` action, which route elsewhere:
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
   `searchId` is an opaque string you choose when you create the surface (it
   only needs to be stable for this surface's lifetime); `stationIds` must
   resolve to at least one id (`context_schema` requires `minItems: 1`) — the
   check above is what keeps that true before the button is even pressable.

## Ids come only from observed evidence

Every id in `/stations`, every `StationMap` point `id`, and every
`StationPicker` option `value` MUST be a station id returned by a tool
(`geo_filter_points_by_radius` or the station catalog search) in this turn.
Never invent, guess, or carry over a station id from a different region or a
prior unrelated search. `searchId` may be any stable opaque string you mint,
but `stationIds` in the delivered event must be a subset of the ids you just
rendered.

## One complete example surface

Ranked points observed for a Los Angeles search (`searchId:
"earthscope-la-20260917"`): `CI01`, `CI02`, `CI03`.

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
        "title": "GNSS stations near Los Angeles",
        "points": [
          {"id": "CI01", "label": "CI01", "latitude": 34.05, "longitude": -118.25},
          {"id": "CI02", "label": "CI02", "latitude": 34.02, "longitude": -118.41},
          {"id": "CI03", "label": "CI03", "latitude": 33.98, "longitude": -118.30}
        ],
        "selected": "CI01"
      },
      {
        "id": "stationsPicker",
        "component": "StationPicker",
        "variant": "multipleSelection",
        "label": "Select stations to analyse",
        "options": [
          {"label": "CI01", "value": "CI01"},
          {"label": "CI02", "value": "CI02"},
          {"label": "CI03", "value": "CI03"}
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
      "searchId": "earthscope-la-20260917",
      "stations": [
        {"id": "CI01", "label": "CI01", "latitude": 34.05, "longitude": -118.25},
        {"id": "CI02", "label": "CI02", "latitude": 34.02, "longitude": -118.41},
        {"id": "CI03", "label": "CI03", "latitude": 33.98, "longitude": -118.30}
      ],
      "selectedStationIds": ["CI01"]
    }
  }
}
```

When the human selects `CI01` and `CI02` and presses the button, the
delivered `earthscope.stations.selected` event context is:

```json
{"searchId": "earthscope-la-20260917", "stationIds": ["CI01", "CI02"]}
```

## After creating the surface

The surface is the question. Once it is `rendered=true` and `state=ready`,
the human's `earthscope.stations.selected` event reaches you either as a new
turn (if you end this turn) or as the answer to a paused question (if you
pause with `ask_user(..., surface_id="earthscope-stations")`) — both are
correct. That event arrives with its meaning already attached (`catalog.clio.json`'s
`narration`, stating that the user picked these stations and wants their
time series staged, profiled, and carried into whatever they originally
asked), so you don't need to infer from the bare event name and context that
this is a request to act rather than a passive report. Pause with `ask_user` when the user asked you to ask or check with
them, or when you have more to do in this same turn once you know their
choice (staging, then plotting) — the selection resumes exactly where you
paused. End the turn with the surface ready when presenting the candidates
is the natural end of what was asked. Either way, never search for or stage
a station series before that structured selection arrives, and every
rendered or staged station id must come from the tool-returned ranked
points, never invented.
