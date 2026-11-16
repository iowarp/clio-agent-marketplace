---
name: after-case-build
event: tool_result
tool: shell_bash
title: Look at the case around the board, and adjust it
description: After the enclosure script runs, tell the agent to look at the case with the board inside in CLIO's 3D view - the openings, standoffs and clearances the fit report measures - and to adjust the script's parameters and run it again.
active: true
---
{% if not tool.is_error and "enclosure.py" in (tool.args.command|default("")) %}The fit report measures the case; it does not show it. Look at the case with the board inside in CLIO's 3D view (`clio.mesh-viewport.v1` on `enclosure.glb`, the base and lid at `nodeOpacity` 0.3 so the board shows through): turn the `camera` to each connector opening (`cutout_*`), the standoffs and the tallest part, and look with `capture_a2ui_surface` (or `look_at_view`); the exploded and sectioned scenes (`--explode`, `--section`) show what the assembled one hides. Change what is wrong in the parameters at the top of `enclosure.py` and run it again, then look again.{% endif %}
