---
name: install-simulator
description: When the SPICE connector finds no simulator, get one onto the machine with the person's consent (ngspice, or LTspice on Windows and macOS), point the connector at it, or skip simulation when the person declines; on Linux, macOS and Windows.
---

# Get a simulator, or skip simulation

The SPICE connector runs a simulator that is already on the machine: ngspice, or LTspice.
When a simulation tool says no simulator was found, its message names the install route for
this system and the setting that points the connector at one (`LTSPICE_MCP_SIMULATOR_EXE`).

## Ask first

Installing software is the person's decision. Ask once with `ask_user` (a choice), naming
the command you would run and where it installs:

- **install it now**: you run the command below for this system;
- **I'll install it myself**: give them the command and wait;
- **skip simulation**: carry on without it, and say in your summary what stays unverified
  (for example a regulator's stability or a filter's corner) so they can simulate later.

If they decline or skip, do not ask again in this conversation.

## Commands, no administrator rights first

| System | Command | Notes |
| --- | --- | --- |
| macOS | `brew install ngspice` | Homebrew installs into the user's prefix, no password |
| Windows | `winget search ngspice` or `winget search LTspice`, then `winget install --id <the id it lists>` | Use the id winget prints; LTspice is the common choice on Windows |
| Linux, any distribution | `conda install -c conda-forge ngspice` (or `mamba` / `micromamba` into a user environment) | No root; works beside a KiCad install |
| Ubuntu, Debian | `pkexec apt-get install -y ngspice` (desktop) or `apt-get install -y ngspice` (root, as in a container) | Administrator rights: see below. On Ubuntu with KiCad's PPA, `ngspice` conflicts with `libngspice-kicad`: use conda instead |
| Fedora | `pkexec dnf install -y ngspice` | Administrator rights: see below |

A folder outside what CLIO may write to: retry with `access_paths` (the folder card). A command
that needs administrator rights, or that the sandbox blocks even with the folders granted (the
result's `boundary` says `elevation_required` or `privilege_denied`): call `shell_bash` again
with `outside_sandbox: true` and an `access_reason`. CLIO shows the person the exact command and
runs it outside the sandbox only if they allow; the system then asks them itself (UAC on
Windows, `pkexec`'s dialog on a Linux desktop, `osascript ... with administrator privileges` on
macOS). CLIO never takes a password: never ask for one in the conversation. If they decline, give them the command to
run in their own terminal, or skip simulation as above.

## Point the connector at it

A simulator on `PATH` is found by itself after the connector restarts. One installed elsewhere
(a conda environment, a user folder) is set in the connector's **Where the simulator is**
value: the full path of `ngspice` (`ngspice.exe` on Windows) or of LTspice's program. Then run
the simulation again.
