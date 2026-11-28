---
name: exploded-teardown
description: Use when someone asks to see how a machine, device or mechanism is put together or works - an exploded view, a teardown, a cutaway, a 3D explainer of a gearbox, an engine, a watch, a pump or a gadget. Builds it from real dimensions as an interactive offline page in the Browser tab or, on request, as a real 3D scene in Blender.
---

# Exploded teardown

One assembly, one spec. The real thing is described once in a JSON spec (parts, shapes,
materials, how each part comes away, what drives the motion); the scripts here turn it
into geometry, and that one geometry feeds both outputs:

- **The interactive page**: one offline HTML file (three.js inlined, no server, no
  network) that the person drives in CLIO's Browser tab: explode slider, the driving
  input, a play button, subsystem chips, part list, steps with a tour, x-ray, section
  cut, labels and camera views.
- **The Blender scene**: the same parts in Blender as a `.blend` with the explode on a
  slider, studio renders and a turntable film. That path is the `teardown-in-blender`
  skill.

`SKILL_ROOT` below is this skill's directory as `load_skill` reports it. The scripts are
standard-library Python, run with CLIO's uv and Python:

```bash
"$CLIO_UV" run --no-project --python "$CLIO_PYTHON" python "SKILL_ROOT/scripts/build_teardown.py" check SPEC.json
"$CLIO_UV" run --no-project --python "$CLIO_PYTHON" python "SKILL_ROOT/scripts/build_teardown.py" html SPEC.json -o PAGE.html
```

```powershell
& $env:CLIO_UV run --no-project --python $env:CLIO_PYTHON python "SKILL_ROOT\scripts\build_teardown.py" check SPEC.json
& $env:CLIO_UV run --no-project --python $env:CLIO_PYTHON python "SKILL_ROOT\scripts\build_teardown.py" html SPEC.json -o PAGE.html
```

## A teardown skill of the person's own

A `teardown` skill the person brings, or one installed in the workspace (for example
`.claude/skills/teardown`), works as written. Two facts save a large download and a failed
install:

- Its Playwright needs a Chromium, and CLIO's browser already installed one:
  `SKILL_ROOT/scripts/find_chromium.py` prints its `path`, which goes in `CHROMIUM` in
  place of `npx playwright install chromium`. `found: false` means CLIO's Chromium is not
  prepared yet; opening any page with the browser once prepares it.
- Where `npm install` in the skill's folder is refused, a workspace folder works
  (`npm --prefix DEPS install`, using the skill's `package.json`) with `TEARDOWN_DEPS` set
  to `DEPS/node_modules`.

CLIO's browser shows its pages as in "Looking at it" below.

## How the person wants to see it

The output is the person's choice (`ask_user`, `kind="choice"`), unless the request
already says, and it holds for the rest of the conversation:

- **Interactive page in the Browser tab**: take it apart in the browser, offline.
- **Real 3D in Blender**: a Blender scene with renders and a film; installs Blender if
  it is not there, with their approval.
- **Both**.

## One real source

A good teardown **starts from a reference, never from imagination**: a service manual, a
patent, a datasheet, a teardown article with measurements, or a standard. The overall
size, the part count and each part's size and position come from it, and the spec's
`source` records it (`name`, `url`, and `estimated` for what was guessed). Without a
source, the result is an honest generic version, labelled as such in the subtitle.

## The spec

It lives at `teardown/<slug>/spec.json` in the workspace. The full schema, every shape and
an example are in `references/spec.md`; what makes a teardown read well is in
`references/craft.md`. In short:

- Millimetres, Z up, the assembly roughly centred on the origin.
- Every part has an `id`, a `name`, a `subsystem`, a `material` and a one-line `note`
  saying what it does. Repeated parts (bolts, balls, blades, teeth) use `repeat`.
- `explode` gives each part a direction, a distance and an `order` (stage), so parts
  come away in the order a person would take them off: covers first, fasteners with
  the cover they hold.
- One `input` drives every motion (a crank angle, a trigger travel, a dial position);
  gear ratios and linkages are numbers in the spec, never keyframes.
- `steps` tell the story in four to eight beats, each focusing a subsystem.
- Shapes come from the spec's numbers, so the same scripts build any assembly;
  per-device code is never needed.

## `check`

`check` prints JSON: part and triangle counts, the size in mm, `overlaps` (parts whose
boxes still overlap when fully exploded), `inside_out_parts` and `notes` (a part with no
note, a spec with no source). An overlap is fixed by a number in the spec (a longer
distance, another direction, a later stage); hiding the part only hides it. A shape error
names the part and field.

## `html`

`html` with `-o teardown/<slug>/<slug>.html` builds the page. The first build downloads
three.js once from the npm registry, checks it against its published sha512 and caches
it; `--three FOLDER` uses an npm `three` package already on disk instead. It prints the
same report plus `page_kb` and `file_url`.

## Looking at it

CLIO's browser opens the page from a `run_code` script once the scene is ready:

```python
url = "FILE_URL"
page = await browser.open(url, label="Teardown")
await page.wait_for_selector('body[data-ready="1"]', timeout=30000)
print(await page.screenshot())
```

Every view state is in the page's hash, so screenshots need no clicks:
`#explode=1`, `#explode=0.6&labels=1`, `#step=2`, `#section=1`, `#xray=1`,
`#input=90`, `#part=PART_ID`, `#hide=ID,ID`, `#view=iso|front|side|top|back`,
`#ui=0` (a clean frame). `await page.goto(url + "#explode=1&labels=1")` changes it; the
scene settles in about 1.5 s, and `await page.reload()` picks up a rebuild. `view_image`
shows each screenshot. The views that reveal problems are assembled, fully exploded with
labels, every step, and the section; the review loop in `references/craft.md` lists what
to look for. A teardown is finished when a full pass over the current build finds nothing.

## What the person gets

`create_artifact` registers the page (`kind="ui_payload"`, `used` naming the spec) and the
best two or three screenshots (`kind="image"`); the page stays open in the Browser tab.
The page's controls are: drag to orbit, the explode slider, the steps, keys `E` explode,
`X` x-ray, `S` section, `L` labels, arrows for steps. The source and what was estimated
are part of the result.

For Blender, or Both, `teardown-in-blender` takes the same spec.
## Credits

The craft rules adapt the community `teardown` skill by elvarofficial
(github.com/elvarofficial/teardown, MIT), whose kit and review rules come from
whaleyxbt/claude-motion (MIT). The page bundles three.js (MIT); its licence is kept
inside every page.
