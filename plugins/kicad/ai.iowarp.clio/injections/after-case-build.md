---
name: after-case-build
event: tool_result
tool: shell_bash
title: The case is worth a look around the board
description: After the enclosure script runs, suggest looking at the case with the board inside in CLIO's 3D view.
active: true
---
{% if not tool.is_error and "enclosure.py" in (tool.args.command|default("")) %}The fit report measures the case but does not show it; `enclosure.glb` in a `clio.mesh-viewport.v1` (base and lid at `nodeOpacity` about 0.3) shows the openings, standoffs and tallest parts with the board inside. The capture reports each part's centre (`parts`) in the view's Y-up frame for aiming the `camera`, and `--explode` and `--section` show what the assembled case hides.{% endif %}
