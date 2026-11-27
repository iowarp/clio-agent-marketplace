---
name: install-blender
description: Install Blender (the 4.5 LTS release) for the teardown's Blender path on Windows, macOS or Linux, for this user and without administrator rights, checked against Blender's published checksums; or the system-wide route when the person prefers it.
---

# Install Blender

Use this when `find_blender.py` (in `teardown-in-blender`) prints `found: false`, or the
person asks to install Blender. `SKILL_ROOT` is this skill's directory as `load_skill`
reports it.

## 1. Plan and ask

Installing software is the person's decision. First print the plan:

```bash
"$CLIO_UV" run --no-project --python "$CLIO_PYTHON" python "SKILL_ROOT/scripts/install_blender.py" --dry-run
```

```powershell
& $env:CLIO_UV run --no-project --python $env:CLIO_PYTHON python "SKILL_ROOT\scripts\install_blender.py" --dry-run
```

It finds the newest point release of the 4.5 LTS series on download.blender.org or one
of Blender's official mirrors, and prints the `version`, the `url`, the `sha256` from
Blender's release checksums, the download `size_mb` and the `folder` it would install
into. Then ask once with `ask_user` (`kind="choice"`), naming the version, size and
folder, with the no-admin route first:

| Choice | What runs |
|---|---|
| **For me only, no admin rights** (recommended) | `install_blender.py` (below): the official archive, checked, unpacked into the user folder |
| **System-wide** | Windows: `winget install --id BlenderFoundation.Blender -e --accept-source-agreements --accept-package-agreements` (Windows asks for approval, UAC). macOS: `brew install --cask blender`. Linux: `flatpak install --user flathub org.blender.Blender` or the distribution's package |
| **No install, renders only** | The `bpy` module route in `teardown-in-blender` (no Blender app) |

## 2. Install

For the user-level route, run it without `--dry-run`:

```bash
"$CLIO_UV" run --no-project --python "$CLIO_PYTHON" python "SKILL_ROOT/scripts/install_blender.py"
```

```powershell
& $env:CLIO_UV run --no-project --python $env:CLIO_PYTHON python "SKILL_ROOT\scripts\install_blender.py"
```

It downloads about 400 MB, so give the shell a long timeout. It writes to the folder in
the plan: on Windows `%USERPROFILE%\AppData\Local\Programs\Blender`, on macOS
`~/Applications/Blender` (the app copied out of the disk image), elsewhere
`~/.local/opt/blender`. When the sandbox blocks that folder, run it again with that
folder in `access_paths`; CLIO asks the person. A checksum mismatch deletes the
download and stops: say so, and never install it another way to get past it. The
JSON it prints last names the `blender` executable; run `find_blender.py` again to
confirm.

`--series` picks another release series (for example a newer LTS) and `--root` another
folder.

For the system-wide route, run the command from the table. It needs administrator
rights, so call the shell with `outside_sandbox: true` and an `access_reason`; CLIO
shows the person the command, and the system asks them itself (UAC on Windows; on macOS
Homebrew's own prompt). Never ask for a password in the conversation. If they decline,
give them the exact command to run in their own terminal, or take the user-level route.

## 3. Remove it

The user-level install is one folder: delete the `Blender` folder named in the plan
(or the `Blender <version>.app` inside it on macOS). Blender keeps its own settings in
the user's config folder, which `--factory-startup` builds never read or write.
