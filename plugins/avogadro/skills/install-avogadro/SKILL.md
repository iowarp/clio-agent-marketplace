---
name: install-avogadro
description: Install Avogadro 2 and the programs its streamed view needs (Xvfb, x11vnc) for the Avogadro connector, with the person's consent, and point the connector at it; when avogadro_status or open_in_avogadro says something is missing (not_installed, display_missing).
keywords: [avogadro, install, xvfb, x11vnc, appimage, level:L2]
---

# Install Avogadro and its streaming programs

The Avogadro connector runs an Avogadro 2 already on the machine on a virtual display and
streams it into the tab; it never installs anything. `avogadro_status` says what is
missing. On Linux it needs three things:

- **Avogadro 2**: the official 2.1.0 build from OpenChemistry, as an AppImage;
- **Xvfb** (the virtual display) and **x11vnc** (streams it): system packages.

macOS and Windows: the streamed view is Linux only (it needs an X display). Avogadro can
still be installed for the person to use on their desktop (`brew install --cask avogadro`,
`winget install --id OpenChemistry.Avogadro2`), and structures move as files.

## 1. Ask first

Installing software is the person's decision: ask once (`ask_user`), naming what you will
install and where (about 110 MB for Avogadro, in a folder in their home; the two system
packages through the package manager). Then run it yourself; the sandbox and the system
each ask the person before anything changes:

- **A folder the sandbox blocks**: retry with `access_paths`; CLIO raises the folder card.
- **Administrator rights, or a block no folder lifts** (the result's `boundary` says
  `elevation_required` or `privilege_denied`): call `shell_bash` again with
  `outside_sandbox: true` and an `access_reason`; on a Linux desktop run the command as
  `pkexec <command>` (the system's authentication dialog); as root in a container no prompt
  is needed. Never ask for a password in the conversation.
- If the person declines, give them the commands to run in their own terminal, or go on
  without Avogadro (Burette's geometry edits cover bond lengths, angles and dihedrals).

## 2. Avogadro 2.1.0 (Linux x86-64, no administrator rights)

Download the release asset, check it, and unpack it (the AppImage needs no FUSE once
unpacked):

```sh
dest="$HOME/.local/opt/avogadro-2.1.0"
mkdir -p "$dest" && cd "$dest"
curl -fL -o Avogadro2-x86_64.AppImage \
  https://github.com/OpenChemistry/avogadrolibs/releases/download/2.1.0/Avogadro2-x86_64.AppImage
echo "712d6f8e4f4481b6d1305a7ce93c9d1ec90109f5507740efccb2d5ce6e9b2823  Avogadro2-x86_64.AppImage" | sha256sum -c -
chmod +x Avogadro2-x86_64.AppImage && ./Avogadro2-x86_64.AppImage --appimage-extract >/dev/null
rm Avogadro2-x86_64.AppImage
```

If the checksum does not match, stop: delete the file, do not run it, and tell the person.
The program is `$dest/squashfs-root/AppRun`.

## 3. Xvfb and x11vnc

| System | Command |
| --- | --- |
| Ubuntu, Debian | `apt-get install -y xvfb x11vnc` (with `pkexec`, or as root in a container) |
| Fedora | `dnf install -y xorg-x11-server-Xvfb x11vnc` |
| Arch | `pacman -S xorg-server-xvfb x11vnc` |

## 4. Point the connector at it

Set the connector's **Where Avogadro is** to the full path of `AppRun` (or of `avogadro2`
when it came from the system's packages), then call `avogadro_status`: it should report
Avogadro and both programs. Then `open_in_avogadro`.
