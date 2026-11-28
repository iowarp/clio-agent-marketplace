---
name: install-blender
description: Install Blender (the 4.5 LTS release) for the teardown's Blender path on Windows, macOS or Linux, for this user and without administrator rights, checked against Blender's published checksums; or the system-wide route when the person prefers it.
---

# Install Blender

This applies when `find_blender.py` (in `teardown-in-blender`) prints `found: false`, or
the person asks to install Blender. `SKILL_ROOT` is this skill's directory as `load_skill`
reports it.

## The plan and the person's choice

Installing software is the person's decision. `--dry-run` prints the plan:

```bash
"$CLIO_UV" run --no-project --python "$CLIO_PYTHON" python "SKILL_ROOT/scripts/install_blender.py" --dry-run
```

```powershell
& $env:CLIO_UV run --no-project --python $env:CLIO_PYTHON python "SKILL_ROOT\scripts\install_blender.py" --dry-run
```

It finds the newest point release of the 4.5 LTS series on download.blender.org or one
of Blender's official mirrors, and prints the `version`, the `url`, the `sha256` from
Blender's release checksums, the download `size_mb` and the `folder` it would install
into. The choice is the person's (`ask_user`, `kind="choice"`, naming the version, size
and folder), with the no-admin route first:

| Choice | What runs |
|---|---|
| **For me only, no admin rights** (recommended) | `install_blender.py` (below): the official archive, checked, unpacked into the user folder |
| **System-wide** | Windows: `winget install --id BlenderFoundation.Blender -e --accept-source-agreements --accept-package-agreements` (Windows asks for approval, UAC). macOS: `brew install --cask blender`. Linux: `flatpak install --user flathub org.blender.Blender` or the distribution's package |
| **No install, renders only** | The `bpy` module route in `teardown-in-blender` (no Blender app) |

## Installing

The user-level route is the same script without `--dry-run`:

```bash
"$CLIO_UV" run --no-project --python "$CLIO_PYTHON" python "SKILL_ROOT/scripts/install_blender.py"
```

```powershell
& $env:CLIO_UV run --no-project --python $env:CLIO_PYTHON python "SKILL_ROOT\scripts\install_blender.py"
```

It downloads about 400 MB, which outlasts a short shell timeout. It writes to the folder
in the plan: on Windows `%USERPROFILE%\AppData\Local\Programs\Blender`, on macOS
`~/Applications/Blender` (the app copied out of the disk image), elsewhere
`~/.local/opt/blender`. A sandbox that blocks that folder lets it through with the folder
in `access_paths`; CLIO asks the person. A checksum mismatch deletes the download and
stops, and the person needs to know; Blender is never installed another way to get past
it. The JSON it prints last names the `blender` executable, and `find_blender.py` then
finds it.

`--series` picks another release series (for example a newer LTS) and `--root` another
folder.

The system-wide route's command from the table needs administrator rights: it runs
through the shell with `outside_sandbox: true` and an `access_reason`; CLIO shows the
person the command, and the system asks them itself (UAC on Windows; on macOS Homebrew's
own prompt). A password never passes through the conversation. A person who declines can
run the exact command in their own terminal, or take the user-level route.

## Removing it

The user-level install is one folder: delete the `Blender` folder named in the plan
(or the `Blender <version>.app` inside it on macOS). Blender keeps its own settings in
the user's config folder, which `--factory-startup` builds never read or write.
