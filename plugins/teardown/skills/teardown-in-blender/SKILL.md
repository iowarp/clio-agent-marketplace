---
name: teardown-in-blender
description: Build an exploded teardown as a real 3D Blender scene - a .blend with the explode on a slider and the mechanism on the timeline, studio renders and a turntable film - from the same spec as the exploded-teardown page. Use when the person picks Blender, or asks for a teardown, exploded view or cutaway in Blender or as renders or a film.
---

# Teardown in Blender

The Blender path of the teardown. It takes the **same spec** as `exploded-teardown`
(write and `check` it there first: `references/spec.md` and `references/craft.md` in
that skill), so the page and the scene always agree. `SKILL_ROOT` is this skill's
directory as `load_skill` reports it.

What it makes, in `teardown/<slug>/blender/`:

- `teardown.blend`: one object per part, a collection per subsystem, real materials, a
  studio, cameras fitted to the parts (assembled, exploded, and with `--animation` a
  film camera) and a **Teardown** empty whose `explode`
  property (0 to 1, in the object's custom properties) drives every part through its
  stages. The timeline plays the mechanism through its input. Each object keeps its
  `part_id`, `subsystem` and `note`, and a **START HERE** text block explains the controls.
- `assembled.png` and `exploded.png`: Cycles renders.
- with `--animation`, `teardown.mp4`: the mechanism running, coming apart, and running
  exploded while the camera swings slowly around it and stays framed (or a `frames/`
  folder of PNGs when this Blender has no FFmpeg). The film renders in Workbench, which
  takes seconds; `--film-engine render` uses the stills engine instead, which takes far longer.
- with `--glb`, `teardown.glb` for other 3D tools.

## 1. Find Blender

```bash
"$CLIO_UV" run --no-project --python "$CLIO_PYTHON" python "SKILL_ROOT/scripts/find_blender.py"
```

```powershell
& $env:CLIO_UV run --no-project --python $env:CLIO_PYTHON python "SKILL_ROOT\scripts\find_blender.py"
```

It prints `{"found": true, "path": ..., "version": ...}` for the newest Blender on this
machine (the `BLENDER` variable, `PATH`, the usual install folders and the user-level
folder `install-blender` uses). When it prints `found: false`, load `install-blender`
and follow it: the person approves the install. Blender 4.2 or later is needed.

## 2. Build the scene

Pass the spec and an output folder after `--`:

```bash
"BLENDER" -b --factory-startup --python-exit-code 2 --python "SKILL_ROOT/scripts/build_blend.py" -- SPEC.json --out teardown/SLUG/blender --animation
```

```powershell
& "BLENDER" -b --factory-startup --python-exit-code 2 --python "SKILL_ROOT\scripts\build_blend.py" -- SPEC.json --out teardown\SLUG\blender --animation
```

`--python-exit-code 2` makes a script error end the command with an error instead of
leaving Blender's exit code 0. The script prints JSON last: `blend`, `assembled`,
`exploded`, `film`, the engine, Blender's version, parts and triangles. A spec error
exits with code 2 and names the part and field: fix the spec and run it again.

Options: `--view iso|front|side|top|back` (default: the spec's `camera`), `--samples`
(96), `--width` and `--height` (1600 x 1000), `--engine eevee` for a faster, rougher
look, `--film-engine workbench|render`, `--glb`, and `--no-render` to save the `.blend` only.
The studio lights and cameras scale with the assembly, so the defaults suit any size. When a
render still needs adjusting, change the spec or these options and build again rather than
writing a separate presentation script.
Stills take under a minute each on a laptop CPU, and the Workbench film well under a
minute. Run the film only when the person wants one.

**When the person does not want a Blender install** but still wants the renders, use
Blender's Python module instead (it needs Python 3.11; uv fetches it):

```bash
"$CLIO_UV" run --no-project --python 3.11 --with "bpy==4.5.*" python "SKILL_ROOT/scripts/build_blend.py" SPEC.json --out teardown/SLUG/blender
```

That writes the same `.blend` and stills, but there is no Blender app to open the
scene in.

## 3. Look at it

Open `assembled.png` and `exploded.png` with `view_image` and apply the review loop in
the craft rules: parts that should touch do, nothing passes through anything, the
assembly fills most of the frame, the accent part reads first, and no large metal
surface blows out to white. Fix the spec (never the scene by hand), and build again.

## 4. Hand it over

Register the renders with `create_artifact` (`kind="image"`), and the film and the
`.blend` (`kind="other"`), each with `used` naming the spec. Tell the person where the
`.blend` is and how to drive it: select the **Teardown** empty, open the Object
properties, Custom Properties, and drag `explode`; press Space to run the mechanism.

If they want it open now, start the Blender app on the file:

```powershell
Start-Process -FilePath "BLENDER" -ArgumentList '"FULL\PATH\teardown.blend"'
```

```bash
"BLENDER" "/full/path/teardown.blend" >/dev/null 2>&1 &
```

(on macOS, `open -a "/path/to/Blender.app" "/full/path/teardown.blend"`). If the
sandbox refuses to start a desktop app, call the shell again with
`outside_sandbox: true` and an `access_reason` saying it opens their teardown in
Blender.
