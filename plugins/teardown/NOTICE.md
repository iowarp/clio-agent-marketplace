# Notices

## elvarofficial/teardown (MIT)

The teardown plugin is CLIO's own implementation: its geometry, page, viewer and Blender
scripts are new code. Its craft and review rules (`skills/exploded-teardown/references/craft.md`,
and the review steps in the skills) are adapted from the community `teardown` skill:

- Repository: https://github.com/elvarofficial/teardown
- Commit: a91262ac1109051e014662d42ecb0b7bc1f113b1
- Licence: MIT, kept verbatim in `LICENSE.upstream`
  (Copyright (c) 2026 elvarofficial; Copyright (c) 2026 whaleyxbt)

That skill's motion kit and review rules come from whaleyxbt/claude-motion (MIT), credited
in the same licence. `upstream.json` records the commit and the checksums of the upstream
files the adaptation was made from. No upstream code or assets are copied into this plugin.

The community skill itself keeps working in CLIO as it is: `exploded-teardown` tells the
agent to follow it as written and to point its `CHROMIUM` and `TEARDOWN_DEPS` settings at
CLIO's browser Chromium and a workspace folder (`scripts/find_chromium.py`).

## three.js (MIT)

Each page this plugin builds inlines three.js, downloaded from the npm registry and checked
against the registry's sha512 before use. Its MIT licence (Copyright three.js authors) is
embedded verbatim in every page, in the `td-licenses` block.

## Blender (GPL)

Blender is not shipped with this plugin. `install-blender` downloads the official release
from download.blender.org or Blender's official mirrors, checked against Blender's
published sha256 checksums, only when the person approves.
