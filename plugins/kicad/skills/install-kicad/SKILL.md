---
name: install-kicad
description: Install KiCad for KiCad MCP Pro on Linux, macOS or Windows, and run it without a screen (headless) so the server's IPC tools work, including how to skip KiCad's first-run wizard.
---

# Install KiCad and run it headless

Use this skill when a KiCad MCP Pro tool says KiCad was not found, when `kicad_session_status`
reports a problem, or when the user asks to set KiCad up on a machine, a container or a server
with no display.

KiCad MCP Pro needs two things from KiCad:

- `kicad-cli`, for exports, ERC and DRC. Every KiCad install has it.
- A KiCad that serves its **IPC API** with the board open, for live edits (moving footprints,
  routing, refilling zones). That is either KiCad's PCB editor (`pcbnew`) with the API server
  turned on, or, from KiCad 11, `kicad-cli api-server`, which needs no display.

With `KICAD_MCP_KICAD_INSTANCE=auto` the server starts that KiCad itself on the first tool that
needs it, and `kicad_session_status` says which way it took. Everything below is what the
server does, so you can do it by hand or tell the user what is missing.

## 1. Install

Installing system software is the person's decision: ask once (`ask_user`), naming the
command, and offer a no-admin route where there is one. Then run it yourself; the sandbox and
the operating system each ask the person before anything changes:

- **A folder the sandbox blocks** (a user-space install, Homebrew's own folders): retry with
  `access_paths`; CLIO raises the folder card.
- **Administrator rights, or a block no folder lifts** (the result's `boundary` says
  `elevation_required` or `privilege_denied`): call `shell_bash` again with
  `outside_sandbox: true` and an `access_reason`. CLIO shows the person the exact command; if
  they allow, it runs outside the sandbox, and the system asks them itself where it needs
  administrator rights: on **Windows**, `winget` raises its UAC prompt; on **macOS**, wrap a
  command that needs `sudo` as `osascript -e 'do shell script "<command>" with administrator
  privileges'` (macOS shows its password dialog); on a **Linux desktop**, run it as
  `pkexec <command>` (the system's authentication dialog). As root in a container no prompt
  is needed. Never ask for a password in the conversation and never pipe one to `sudo`.
- If the person declines, give them the exact command to run in their own terminal, or use
  the no-admin route.

| System | Command | Notes |
| --- | --- | --- |
| Ubuntu, Debian | `sudo add-apt-repository ppa:kicad/kicad-10.0-releases && sudo apt update && sudo apt install --no-install-recommends kicad kicad-symbols kicad-footprints kicad-templates` | `kicad-packages3d` adds the 3D models (several GB); install it only when 3D views or STEP exports need component bodies |
| Ubuntu, nightly (KiCad 11 preview, for `api-server`) | `sudo add-apt-repository ppa:kicad/kicad-dev-nightly && sudo apt install kicad-nightly` | Installs beside KiCad 10 as `kicad-cli-nightly`, `pcbnew-nightly` |
| Fedora | `sudo dnf install kicad` | |
| Arch | `sudo pacman -S kicad kicad-library` | |
| macOS | `brew install --cask kicad` | `--appdir=~/Applications` installs without administrator rights. Or the disk image from kicad.org. `kicad-cli` is in `<Applications>/KiCad/KiCad.app/Contents/MacOS/` |
| Windows | `winget install --id KiCad.KiCad -e --accept-source-agreements --accept-package-agreements` | Machine-wide, so Windows asks for approval (UAC). `kicad-cli.exe` is in `C:\Program Files\KiCad\<version>\bin\` |
| Conda (no admin rights) | `conda install -c conda-forge kicad` | A user-space install; useful where installing system packages is not allowed |

**Disk space for the 3D models.** The 3D model package is several gigabytes once unpacked,
more than the rest of KiCad together. Before installing it, read its size
(`apt-cache show kicad-packages3d`, field `Installed-Size`, in kB; on macOS and Windows the
models come with the installer) and the free space where it goes (`df -h /usr` on Linux and
macOS, `Get-PSDrive C` on Windows), and tell the person both. When the space is short, offer
the choice: skip the models (the 3D view and STEP export then show the board, tracks and
pads without component bodies), or let the person free space. Never free space yourself by
deleting folders you did not create, and never CLIO's own folders: a running connector's
environment lives there.

If `add-apt-repository` fails (for example `No module named 'apt_pkg'` when the system Python
was replaced), add the PPA by hand: put
`deb [signed-by=/etc/apt/keyrings/kicad.gpg] https://ppa.launchpadcontent.net/kicad/kicad-10.0-releases/ubuntu <codename> main`
in `/etc/apt/sources.list.d/kicad.list` and the PPA's signing key (its fingerprint is in the
Launchpad API, `https://api.launchpad.net/1.0/~kicad/+archive/ubuntu/kicad-10.0-releases`,
field `signing_key_fingerprint`) in `/etc/apt/keyrings/kicad.gpg`.

On Ubuntu, the `ngspice` package conflicts with KiCad's own `libngspice-kicad`. For circuit
simulation, install ngspice through conda instead (the spice plugin's `install-simulator`).

If the server did not find an install, point it at the CLI: `KICAD_CLI_PATH=/path/to/kicad-cli`.
Setting it also makes the server use only that install when it starts KiCad.

## 2. Run KiCad with no screen

There are two ways; the server takes the first that works.

**KiCad 11 or later: `kicad-cli api-server`.** No display, no window, no wizard:

```bash
KICAD_CONFIG_HOME=/path/to/private-settings kicad-cli api-server --socket /path/to/api.sock board.kicad_pcb
```

`--socket` takes a plain file path. Clients connect to `ipc:///path/to/api.sock`.

**KiCad 10: the PCB editor on a virtual display.** Install Xvfb (`apt install xvfb`), then:

```bash
KICAD_CONFIG_HOME=/path/to/private-settings xvfb-run -a -s "-screen 0 1600x1000x24" pcbnew board.kicad_pcb
```

The editor serves its API socket under its temp folder: `$TMPDIR/kicad/api.sock` (usually
`/tmp/kicad/api.sock`) on Linux and macOS, `%TEMP%\kicad\api.sock` on Windows. It does not read
`KICAD_API_SOCKET`, so a KiCad started with another temp folder (a sandboxed client) listens
there.

## 3. Skip the first-run wizard (headless)

**There is no command-line flag or environment variable that skips KiCad's first-run wizard.**
On a first start, or when settings files are missing, `pcbnew` opens "Welcome to KiCad", and
while that dialog is open every IPC call answers **"KiCad is not ready to reply"**. On a machine
with no screen nobody can click it.

The wizard is skipped by giving KiCad a settings folder that is already complete. Use a private
folder through `KICAD_CONFIG_HOME`, so the user's own settings are never touched, and put these
in `<KICAD_CONFIG_HOME>/<major>.<minor>/` (for example `10.0/`):

1. `kicad_common.json`:

   ```json
   {"api": {"enable_server": true},
    "do_not_show_again": {"data_collection_prompt": true, "update_check_prompt": true}}
   ```

   `api.enable_server` is the setting behind Preferences > Plugins > Enable KiCad API.
2. `sym-lib-table` and `fp-lib-table`, copied from KiCad's `template` folder
   (`/usr/share/kicad/template/` on Linux).
3. `design-block-lib-table`. KiCad 10 ships no template for it, and **without it the wizard
   appears even when the other files are there.** An empty table is enough:

   ```
   (design_block_lib_table
   	(version 7)
   )
   ```

`kicad-cli api-server` never shows the wizard, but the same folder keeps its settings separate.

## 4. Things that block a start

- **"PCB ... is already open by user at host"**: a KiCad that was killed left
  `~<board>.kicad_pcb.lck` and `~<board>.kicad_pro.lck` beside the board. A lock names a host and
  a user, not a process: when it names this host and no KiCad has the board open, delete it.
- **No display and no Xvfb**: install Xvfb, or KiCad 11's `api-server`.
- **Root in a sandbox**: `apt` writes `/usr`, `/etc` and `/var/lib/dpkg` and replaces files its
  own download account owns, which a sandboxed command cannot do even with the folders granted
  (`privilege_denied`). Run the install outside the sandbox with the person's allow (step 1).

## 5. Check it

Call `kicad_session_status` (with `start: true` to start KiCad now). It reports the case
(`attached`, `headless`, `xvfb` or `window`), KiCad's version, the process the server started
and its private settings folder, or what is missing and what to do. A KiCad the server started
stops when the server stops; one it attached to is never stopped.
