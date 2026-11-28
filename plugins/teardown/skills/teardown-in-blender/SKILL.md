---
name: teardown-in-blender
description: Build an exploded teardown as a real 3D Blender scene - a .blend with the explode on a slider and the mechanism on the timeline, studio renders and a turntable film - from the same spec as the exploded-teardown page. Use when the person picks Blender, or asks for a teardown, exploded view or cutaway in Blender or as renders or a film.
---

# Teardown in Blender

The Blender path of the teardown. It takes the **same spec** as `exploded-teardown`
(written and `check`ed there: `references/spec.md` and `references/craft.md` in that
skill), so the page and the scene always agree. `SKILL_ROOT` is this skill's
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

## Finding Blender

```bash
"$CLIO_UV" run --no-project --python "$CLIO_PYTHON" python "SKILL_ROOT/scripts/find_blender.py"
```

```powershell
& $env:CLIO_UV run --no-project --python $env:CLIO_PYTHON python "SKILL_ROOT\scripts\find_blender.py"
```

It prints `{"found": true, "path": ..., "version": ...}` for the newest Blender on this
machine (the `BLENDER` variable, `PATH`, the usual install folders and the user-level
folder `install-blender` uses). `found: false` is where `install-blender` comes in; the
person approves the install. Blender 4.2 or later is needed.

## Building the scene

The spec and an output folder go after `--`:

```bash
"BLENDER" -b --factory-startup --python-exit-code 2 --python "SKILL_ROOT/scripts/build_blend.py" -- SPEC.json --out teardown/SLUG/blender --animation
```

```powershell
& "BLENDER" -b --factory-startup --python-exit-code 2 --python "SKILL_ROOT\scripts\build_blend.py" -- SPEC.json --out teardown\SLUG\blender --animation
```

`--python-exit-code 2` makes a script error end the command with an error instead of
leaving Blender's exit code 0. The script prints JSON last: `blend`, `assembled`,
`exploded`, `film`, the engine, Blender's version, parts and triangles. A spec error
exits with code 2 and names the part and field.

Options: `--view iso|front|side|top|back` (default: the spec's `camera`), `--samples`
(96), `--width` and `--height` (1600 x 1000), `--engine eevee` for a faster, rougher
look, `--film-engine workbench|render`, `--glb`, and `--no-render` to save the `.blend` only.
The studio lights and cameras scale with the assembly, so the defaults suit any size; the
spec and these options cover adjustments without a separate presentation script.
Stills take under a minute each on a laptop CPU, and the Workbench film well under a
minute. The film is for when the person wants one.

**When the person does not want a Blender install** but still wants the renders,
Blender's Python module works instead (it needs Python 3.11; uv fetches it):

```bash
"$CLIO_UV" run --no-project --python 3.11 --with "bpy==4.5.*" python "SKILL_ROOT/scripts/build_blend.py" SPEC.json --out teardown/SLUG/blender
```

That writes the same `.blend` and stills, but there is no Blender app to open the
scene in.

## Looking at it

`view_image` shows `assembled.png` and `exploded.png`; the review loop in the craft rules
applies: parts that should touch do, nothing passes through anything, the assembly fills
most of the frame, the accent part reads first, and no large metal surface blows out to
white. A fix belongs in the spec; a scene edited by hand no longer matches the page.

## What the person gets

`create_artifact` registers the renders (`kind="image"`), and the film and the `.blend`
(`kind="other"`), each with `used` naming the spec. The person drives the `.blend` by
selecting the **Teardown** empty, opening the Object properties, Custom Properties, and
dragging `explode`; Space runs the mechanism.

The Blender app opens on the file with:

```powershell
Start-Process -FilePath "BLENDER" -ArgumentList '"FULL\PATH\teardown.blend"'
```

```bash
"BLENDER" "/full/path/teardown.blend" >/dev/null 2>&1 &
```

(on macOS, `open -a "/path/to/Blender.app" "/full/path/teardown.blend"`). A sandbox that
refuses to start a desktop app allows it through the shell with `outside_sandbox: true`
and an `access_reason` saying it opens their teardown in Blender.
