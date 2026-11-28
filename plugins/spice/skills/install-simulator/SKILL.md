---
name: install-simulator
description: When the SPICE connector finds no simulator, look for one elsewhere on the machine and point the connector at it, or get one with the person's consent (ngspice, or LTspice on Windows and macOS), or skip simulation when the person declines; on Linux, macOS and Windows.
---

# Get a simulator, or skip simulation

The SPICE connector runs a simulator that is already on the machine: ngspice, or LTspice.
When a simulation tool says no simulator was found, its message names the install route for
this system and the setting that points the connector at one (`LTSPICE_MCP_SIMULATOR_EXE`).

## Where a simulator may already be

"No simulator was found" means only that the connector found none where it looks: its
**Where the simulator is** value, PATH and the simulators' standard install folders. A
simulator may be elsewhere: ngspice in a conda environment (`conda env list`) or a Homebrew
prefix outside PATH, LTspice copied or installed in another folder or drive, or under Wine.
The person may also know where `ngspice` or LTspice's program (`LTspice.exe`) is. Using one
that is found is the person's decision (`ask_user`, naming its path). **Where the simulator
is** (`simulator`) holds the full path of `ngspice` (`ngspice.exe` on Windows) or of LTspice's
program, set with `set_connector_value`; the value belongs to this conversation, and the
person can save it as their default in the SPICE connector's settings.

## The person's choice

Installing software is the person's decision (`ask_user`, a choice naming the command and
where it installs):

- **install it now**: the agent runs the command below for this system;
- **I'll install it myself**: the person runs the command;
- **skip simulation**: the work goes on without it, and what stays unverified (for example a
  regulator's stability or a filter's corner) is something the person can simulate later.

A person who declined or skipped has answered for this conversation.

## Commands, no administrator rights first

| System | Command | Notes |
| --- | --- | --- |
| macOS | `brew install ngspice` | Homebrew installs into the user's prefix, no password |
| Windows | `winget search ngspice` or `winget search LTspice`, then `winget install --id <the id it lists>` | Use the id winget prints; LTspice is the common choice on Windows |
| Linux, any distribution | `conda install -c conda-forge ngspice` (or `mamba` / `micromamba` into a user environment) | No root; works beside a KiCad install |
| Ubuntu, Debian | `pkexec apt-get install -y ngspice` (desktop) or `apt-get install -y ngspice` (root, as in a container) | Administrator rights: see below. On Ubuntu with KiCad's PPA, `ngspice` conflicts with `libngspice-kicad`: use conda instead |
| Fedora | `pkexec dnf install -y ngspice` | Administrator rights: see below |

A folder outside what CLIO may write to is reachable with `access_paths` (the folder card). A
command that needs administrator rights, or that the sandbox blocks even with the folders
granted (the result's `boundary` says `elevation_required` or `privilege_denied`), runs through
`shell_bash` with `outside_sandbox: true` and an `access_reason`. CLIO shows the person the exact command and
runs it outside the sandbox only if they allow; the system then asks them itself (UAC on
Windows, `pkexec`'s dialog on a Linux desktop, `osascript ... with administrator privileges` on
macOS). CLIO never takes a password, and a password never passes through the conversation. A
person who declines can run the command in their own terminal, or skip simulation as above.

## After installing

A simulator on `PATH` is found by itself after the connector restarts. One installed elsewhere
(a conda environment, a user folder) is set as in "Where a simulator may already be".
