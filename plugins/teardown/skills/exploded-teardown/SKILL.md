---
name: exploded-teardown
description: Use when someone asks to see how a machine, device or mechanism is put together or works - an exploded view, a teardown, a cutaway, a 3D explainer of a gearbox, an engine, a watch, a pump or a gadget. Builds it from real dimensions as an interactive offline page in the Browser tab or, on request, as a real 3D scene in Blender.
---

# Exploded teardown

One assembly, one spec. You describe the real thing once in a JSON spec (parts, shapes,
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
standard-library Python; run them with CLIO's uv and Python:

```bash
"$CLIO_UV" run --no-project --python "$CLIO_PYTHON" python "SKILL_ROOT/scripts/build_teardown.py" check SPEC.json
"$CLIO_UV" run --no-project --python "$CLIO_PYTHON" python "SKILL_ROOT/scripts/build_teardown.py" html SPEC.json -o PAGE.html
```

```powershell
& $env:CLIO_UV run --no-project --python $env:CLIO_PYTHON python "SKILL_ROOT\scripts\build_teardown.py" check SPEC.json
& $env:CLIO_UV run --no-project --python $env:CLIO_PYTHON python "SKILL_ROOT\scripts\build_teardown.py" html SPEC.json -o PAGE.html
```

## A teardown skill of the person's own

If the person asks for their own or a community `teardown` skill, or one is installed in
the workspace (for example `.claude/skills/teardown`), follow that skill as written. Two
things save a large download and a failed install:

- Its Playwright needs a Chromium, and CLIO's browser already installed one. Run
  `SKILL_ROOT/scripts/find_chromium.py` and set `CHROMIUM` to the `path` it prints
  instead of running `npx playwright install chromium`. If it prints `found: false`,
  open any page with the browser once (that prepares CLIO's Chromium) and run it again.
- When `npm install` in the skill's folder is refused, install into a workspace folder
  instead (`npm --prefix DEPS install`, using the skill's `package.json`) and set
  `TEARDOWN_DEPS` to `DEPS/node_modules`.

Check its pages with CLIO's browser, as in step 6 below.

## 1. Ask how they want to see it

Unless the request already says, ask once with `ask_user` (`kind="choice"`) before any
work:

- **Interactive page in the Browser tab**: take it apart in the browser, offline.
- **Real 3D in Blender**: a Blender scene with renders and a film; installs Blender if
  it is not there, with their approval.
- **Both**.

Keep the answer for the rest of the conversation.

## 2. Find one real source

Rule one of a good teardown: **start from a reference, never from imagination**. Find
one source for the real thing: a service manual, a patent, a datasheet, a teardown
article with measurements, or a standard. Take the overall size, the part count and
each part's size and position from it, and note what you estimated. Record it in the
spec's `source` (`name`, `url`, and `estimated` for what you had to guess). If nothing
can be found, say so and build an honest generic version with that label in the
subtitle.

## 3. Write the spec

Write `teardown/<slug>/spec.json` in the workspace. The full schema, every shape and an
example are in `references/spec.md`; the craft rules (what makes a teardown read well)
are in `references/craft.md`. Read both before the first spec. In short:

- Millimetres, Z up, the assembly roughly centred on the origin.
- Every part has an `id`, a `name`, a `subsystem`, a `material` and a one-line `note`
  saying what it does. Repeated parts (bolts, balls, blades, teeth) use `repeat`.
- `explode` gives each part a direction, a distance and an `order` (stage), so parts
  come away in the order a person would take them off: covers first, fasteners with
  the cover they hold.
- One `input` drives every motion (a crank angle, a trigger travel, a dial position);
  gear ratios and linkages are numbers in the spec, never keyframes.
- `steps` tell the story in four to eight beats, each focusing a subsystem.
- Stay general: shapes come from the spec's numbers, so the same scripts build any
  assembly. Never write per-device code.

## 4. Check it

Run `check`. It prints JSON: part and triangle counts, the size in mm, `overlaps`
(parts whose boxes still overlap when fully exploded), `inside_out_parts` and `notes`
(a part with no note, a spec with no source). Fix every overlap with a number in the
spec (a longer distance, another direction, a later stage), never by hiding the part.
A shape error names the part and field.

## 5. Build the page

Run `html` with `-o teardown/<slug>/<slug>.html`. The first build downloads three.js
once from the npm registry, checks it against its published sha512 and caches it; pass
`--three FOLDER` to use an npm `three` package already on disk instead. It prints the
same report plus `page_kb` and `file_url`.

## 6. Look at it in the browser

Open the page in CLIO's browser from a `run_code` script and wait for the scene:

```python
url = "FILE_URL"
page = await browser.open(url, label="Teardown")
await page.wait_for_selector('body[data-ready="1"]', timeout=30000)
print(await page.screenshot())
```

Every view state is in the page's hash, so screenshots need no clicks:
`#explode=1`, `#explode=0.6&labels=1`, `#step=2`, `#section=1`, `#xray=1`,
`#input=90`, `#part=PART_ID`, `#hide=ID,ID`, `#view=iso|front|side|top|back`,
`#ui=0` (a clean frame). Change it with `await page.goto(url + "#explode=1&labels=1")`,
wait about 1.5 s, and screenshot again. Look at each with `view_image`: assembled,
fully exploded with labels, every step, and the section. Check that parts that should
touch do, nothing passes through anything, labels do not cover their parts, and the
assembly fills most of the frame. Fix the spec, rebuild, reload (`await page.reload()`)
and look again; stop when a full pass finds nothing.

## 7. Hand it over

Register the page with `create_artifact` (`kind="ui_payload"`, `used` naming the spec)
and the best two or three screenshots (`kind="image"`), leave the page open in the
Browser tab, and say in a few lines what the person can do with it (drag to orbit,
the explode slider, the steps, keys `E` explode, `X` x-ray, `S` section, `L` labels,
arrows for steps). Name the source and what was estimated.

For Blender, or Both, load `teardown-in-blender` and give it the same spec.

## Credits

The craft rules adapt the community `teardown` skill by elvarofficial
(github.com/elvarofficial/teardown, MIT), whose kit and review rules come from
whaleyxbt/claude-motion (MIT). The page bundles three.js (MIT); its licence is kept
inside every page.
