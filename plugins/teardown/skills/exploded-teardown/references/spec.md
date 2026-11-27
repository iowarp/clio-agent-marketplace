# The teardown spec

One JSON file describes the assembly. `build_teardown.py check` validates it and names
the part and field of any mistake. Every length is in the spec's `units`; angles are
degrees; Z is up.

## Top level

| Key | Meaning |
|---|---|
| `title` | Required. The assembly's name. |
| `subtitle`, `summary` | One line under the title; a short paragraph for the info panel. |
| `units` | `mm` (default), `cm`, `m` or `in`. |
| `source` | `{"name", "url", "estimated"}`: the one reference the numbers come from and what was guessed. `check` notes a spec with none. |
| `accent` | The one accent colour (default `#d4552b`), for the part doing the work. |
| `background` | Page and render background (default `#ecebe6`). |
| `camera` | `{"view": "iso|front|side|top|back"}` or `{"direction": [x, y, z]}` (from the target towards the camera). |
| `input` | The one value that drives every motion: `{"name", "unit" ("deg"), "min" (0), "max" (360), "default", "periodic" (true), "seconds" (6, one cycle when playing)}`. |
| `subsystems` | `[{"id", "name", "color", "note"}]`. When listed, every part must name one of them. |
| `parts` | Required, non-empty. See below. |
| `steps` | The story, in four to eight beats. See below. |

## Parts

```json
{"id": "pinion", "name": "Input pinion", "subsystem": "drive", "material": "steel",
 "note": "Turned by the crank; drives the wheel 2:1.", "accent": true,
 "position": [-20, 0, 10], "rotation": [0, 0, 0],
 "shape": {"type": "gear", "teeth": 12, "module": 2, "thickness": 12, "bore": 6},
 "motion": {"type": "rotate", "axis": [0, 0, 1], "ratio": 1},
 "explode": {"direction": [0, 0, 1], "distance": 40, "order": 1}}
```

| Key | Meaning |
|---|---|
| `id` | Unique. Repeated copies become `<id>-1` ... `<id>-n`. |
| `name`, `note` | Shown on hover, in the part list and on labels. `note` says what the part does. |
| `subsystem` | Groups parts for the chips, steps and colours. |
| `material` | `steel`, `aluminium`, `cast-iron`, `brass`, `copper`, `gold`, `chrome`, `plastic`, `rubber`, `glass`, `pcb`, `ceramic`, `wood` or `painted`. |
| `color` | Optional hex colour over the material's own. |
| `accent` | Paint this part in the accent colour. Use it for one part or one small group. |
| `cutaway` | This part is cut in half by the section view (housings, covers, cases). When no part is marked, the section cuts everything. |
| `position`, `rotation` | Where the part sits: a translation and XYZ Euler angles applied to all its shapes. |
| `shape` / `shapes` | One shape, or a list. Each shape can have its own `position` and `rotation` inside the part. |
| `repeat` | Copies of the part. See below. |
| `explode` | How it comes away. See below. |
| `motion` | How the input moves it. See below. |

### Shapes

Every shape takes optional `position`, `rotation` and `segments` (smoothness of curves).

| `type` | Fields | Frame |
|---|---|---|
| `box` | `size [x, y, z]` | Centred on its origin. |
| `cylinder` | `radius`, `height` | Base at z = 0, up +Z. |
| `tube` | `outer_radius`, `inner_radius`, `height` | Base at z = 0. |
| `cone` | `radius_bottom`, `radius_top` (0), `height` | Base at z = 0. |
| `sphere` | `radius` | Centred. |
| `torus` | `radius` (to the tube's centre), `tube`, `tube_segments` | In the XY plane. |
| `lathe` | `profile [[r, z], ...]`, `closed` (true) | Revolved about Z. Housings, pistons, bottles, knobs, shafts with steps. |
| `extrude` | `outline [[x, y], ...]`, `holes`, `thickness` | XY outline from z = 0 up. Holes are point lists or `{"circle": [cx, cy, r]}`. Plates, brackets, links, cams. |
| `gear` | `teeth`, `module`, `thickness`, `pressure_angle` (20), `bore`, `holes` | Involute spur gear, from z = 0 up. Pitch radius = module x teeth / 2; meshing centres sit at the sum of the pitch radii. |
| `hex` | `across_flats`, `height`, `bore` | Nuts and bolt heads, from z = 0 up. |
| `rod` | `from [x, y, z]`, `to [x, y, z]`, `radius` | Shafts, pins, axles, connecting rods. |
| `sweep` | `path [[x, y, z], ...]`, `radius`, `closed` | A round section along a path: pipes, hoses, wires, belts, chains. |
| `spring` | `radius` (coil), `wire`, `pitch`, `turns` | Coil from z = 0 up. |
| `stl` | `path` (relative to the spec) | A real part's mesh, when one is available. |

### Repeat

`{"count", "axis" ([0,0,1]), "center" ([0,0,0]), "angle", "offset", "input_step"}`

- A ring of copies: `count` around `axis` through `center`; `angle` is 360 by default
  (evenly spaced, no duplicate at the end), or a smaller arc.
- A row of copies: `offset [x, y, z]` between neighbours (the angle is then 0 unless
  given).
- `input_step` shifts each copy's motion by that much input, so pistons, cams or blades
  run out of phase (for a four-cylinder crank, `input_step: 180`).

At most 500 copies per part.

### Explode

`{"direction", "distance", "order"}`

- `direction` defaults to straight away from the assembly's centre.
- `distance` defaults to 0.35 of the assembly's diagonal.
- `order` is the stage, from 0. At explode 0 to 1 the stages come away one after
  another, so give the outer parts 0, what they hold 1, and so on. A fastener takes the
  same order as the part it holds, and a slightly longer distance.

### Motion

Every motion is a function of the one `input`, so it needs a top-level `input`.

| `type` | Fields | What it does |
|---|---|---|
| `rotate` | `axis`, `pivot`, `ratio` (1), `offset` (0) | Angle = ratio x input + offset, about `axis` through `pivot`. Gear pairs: ratio = -(driver teeth / driven teeth). |
| `slide` | `axis`, `amplitude`, `ratio` (1), `phase` (0) | Travel along `axis` = amplitude x sin(ratio x input + phase). A piston's slider-crank is close to this. |
| `rigid` | `table [[input, dx, dy, dz, angle], ...]`, `axis`, `pivot` | Any linkage or cam: a table of offsets and an angle about `axis`, interpolated. |

`pivot` defaults to the part's `position`. `rotate` and `slide` can also take a
`table [[input, value], ...]` instead of the formula. Tables wrap when the input is
periodic. When gears mesh, set the driven gear's `offset` to half a tooth pitch in
degrees (180 / teeth) if the teeth clash at input 0.

## Steps

```json
{"title": "The gear pair", "text": "The pinion turns the wheel at half speed.",
 "explode": 0.4, "input": 90, "focus": ["drive"], "view": "iso", "section": false}
```

`focus` names parts, subsystems or a repeated part's base id; everything else fades.
`explode`, `input`, `view` and `section` set the scene for the beat. Start assembled,
open up the part doing the work, end fully exploded.

## A small complete example

```json
{
  "title": "Spur gear reducer", "subtitle": "2:1, two gears in a cast case",
  "units": "mm",
  "source": {"name": "A catalogue drawing", "url": "https://example.org/reducer", "estimated": "wall thickness"},
  "input": {"name": "Input shaft", "unit": "deg", "min": 0, "max": 360},
  "subsystems": [{"id": "case", "name": "Case"}, {"id": "drive", "name": "Gear train"},
                 {"id": "fasteners", "name": "Fasteners"}],
  "parts": [
    {"id": "housing", "name": "Housing", "subsystem": "case", "material": "cast-iron",
     "cutaway": true, "note": "Holds the bearings and the oil.",
     "shape": {"type": "tube", "outer_radius": 60, "inner_radius": 55, "height": 40},
     "explode": {"direction": [0, 0, -1], "distance": 60, "order": 0}},
    {"id": "lid", "name": "Lid", "subsystem": "case", "material": "aluminium",
     "note": "Closes the case.", "position": [0, 0, 40],
     "shape": {"type": "cylinder", "radius": 60, "height": 4},
     "explode": {"direction": [0, 0, 1], "distance": 80, "order": 0}},
    {"id": "bolt", "name": "Lid bolt", "subsystem": "fasteners", "material": "steel",
     "note": "Holds the lid down.", "position": [57.5, 0, 44],
     "shapes": [{"type": "hex", "across_flats": 7, "height": 4},
                {"type": "cylinder", "radius": 2, "height": 12, "position": [0, 0, -12]}],
     "repeat": {"count": 6, "axis": [0, 0, 1]},
     "explode": {"direction": [0, 0, 1], "distance": 110, "order": 0}},
    {"id": "pinion", "name": "Pinion", "subsystem": "drive", "material": "steel",
     "accent": true, "note": "Input, 12 teeth.", "position": [-18, 0, 10],
     "shape": {"type": "gear", "teeth": 12, "module": 2, "thickness": 12, "bore": 6},
     "motion": {"type": "rotate", "axis": [0, 0, 1], "ratio": 1},
     "explode": {"direction": [0, 0, 1], "distance": 40, "order": 1}},
    {"id": "wheel", "name": "Wheel", "subsystem": "drive", "material": "brass",
     "note": "Output, 24 teeth: half speed.", "position": [18, 0, 10],
     "shape": {"type": "gear", "teeth": 24, "module": 2, "thickness": 12, "bore": 8},
     "motion": {"type": "rotate", "axis": [0, 0, 1], "ratio": -0.5, "offset": 7.5},
     "explode": {"direction": [0, 0, 1], "distance": 60, "order": 1}}
  ],
  "steps": [
    {"title": "Closed", "text": "A cast case with a bolted lid.", "explode": 0},
    {"title": "Lid off", "text": "Six bolts hold the lid.", "explode": 0.5, "focus": ["lid", "bolt"]},
    {"title": "The pair", "text": "The pinion drives the wheel at half speed.",
     "explode": 0.5, "focus": ["drive"], "section": true},
    {"title": "Every part", "explode": 1}
  ]
}
```

The pinion's pitch radius is 2 x 12 / 2 = 12 and the wheel's is 2 x 24 / 2 = 24, so
their centres are 36 apart (-18 and 18).
