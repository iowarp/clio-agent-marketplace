---
name: install-avogadro
description: Find Avogadro 2 if it is already installed, otherwise install it and the programs its streamed view needs (Xvfb, x11vnc, OpenGL libraries) where every conversation finds it, with the person's consent; when avogadro_status or open_in_avogadro says something is missing (not_installed, display_missing).
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

## Avogadro already on the machine

`not_installed` means only that `avogadro_status` found no Avogadro where it looks: the
connector's **Where Avogadro is**, `avogadro2` on PATH, and where this skill installs it
(`~/.local/opt/avogadro-<version>/squashfs-root/AppRun`). Avogadro may be elsewhere: an
AppImage in Downloads or `/opt`, an unpacked `squashfs-root`, a distribution package outside
PATH. `find ~ /opt -maxdepth 4 -iname 'avogadro2*'` and the AppRun of any unpacked copy
turn these up; the person may know of a copy they do not.

Whether to use a found copy or install another is the person's choice (`ask_user`).
**Where Avogadro is** (`avogadro`), set to a copy's path with `set_connector_value`, makes
`avogadro_status` find it; the value belongs to this conversation, and the person can save
it as their default in the Avogadro connector's settings. What `avogadro_status` still
reports missing is what remains to install (often only the display programs).

## Consent and permissions

Installing software is the person's decision (`ask_user`). What goes where: about 110 MB
for Avogadro, in a folder in their home; the two system packages through the package
manager. The sandbox and the system each ask the person before an install changes
anything:

- **A folder the sandbox blocks**: retry with `access_paths`; CLIO raises the folder card.
- **Administrator rights, or a block no folder lifts** (the result's `boundary` says
  `elevation_required` or `privilege_denied`): call `shell_bash` again with
  `outside_sandbox: true` and an `access_reason`; on a Linux desktop run the command as
  `pkexec <command>` (the system's authentication dialog); as root in a container no prompt
  is needed. The dialog takes the password from the person directly, so it never passes
  through the conversation.
- A person who declines can run the commands in their own terminal, or work without
  Avogadro (Burette's geometry edits cover bond lengths, angles and dihedrals).

## Avogadro 2.1.0 (Linux x86-64, no administrator rights)

The release asset, checked and unpacked (the AppImage needs no FUSE once unpacked):

```sh
dest="$HOME/.local/opt/avogadro-2.1.0"
mkdir -p "$dest" && cd "$dest"
curl -fL -o Avogadro2-x86_64.AppImage \
  https://github.com/OpenChemistry/avogadrolibs/releases/download/2.1.0/Avogadro2-x86_64.AppImage
echo "712d6f8e4f4481b6d1305a7ce93c9d1ec90109f5507740efccb2d5ce6e9b2823  Avogadro2-x86_64.AppImage" | sha256sum -c -
chmod +x Avogadro2-x86_64.AppImage && ./Avogadro2-x86_64.AppImage --appimage-extract >/dev/null
rm Avogadro2-x86_64.AppImage
```

A checksum that does not match means the file is not the published release; it is not
safe to run, and the person needs to know. The program is `$dest/squashfs-root/AppRun`. A
launcher on PATH lets every conversation and the person's own terminal find it:

```sh
mkdir -p "$HOME/.local/bin" && ln -sf "$dest/squashfs-root/AppRun" "$HOME/.local/bin/avogadro2"
```

## Xvfb and x11vnc

| System | Command |
| --- | --- |
| Ubuntu, Debian | `apt-get install -y xvfb x11vnc libopengl0 libegl1` (with `pkexec`, or as root in a container) |
| Fedora | `dnf install -y xorg-x11-server-Xvfb x11vnc libglvnd-opengl libglvnd-egl` |
| Arch | `pacman -S xorg-server-xvfb x11vnc libglvnd` |

The official build loads the system's OpenGL libraries (`libOpenGL.so.0`, `libEGL.so.1`);
on a minimal system they are missing and Avogadro exits at start.
`ldd "$dest/squashfs-root/usr/bin/avogadro2" | grep "not found"` lists what is missing.

## Checking it

Installed as above, `avogadro_status` finds Avogadro and both programs with no setting,
in this conversation and every later one, and `open_in_avogadro` can open it.
