---
name: after-drc
event: tool_result
tool: kicad_run_drc
title: Look at each violation, and record the pass
description: After DRC, tell the agent to look at the violations where they are on the board and to record a placement or routing pass in the science log.
active: true
---
{% if not tool.is_error %}See each violation where it is: the checks view (`view_checks`) lists them, and the board view (`view_board`) shows them in place with `focus` on the parts or nets involved and its `capture` (or `look_at_view`); fix each at its cause by hand. When this DRC ends a placement or routing pass, record the pass in the science log with its measured values (unrouted, ratsnest length, DRC count, vias, track length) and write its row to the placement metrics the workbench chart reads, as `pcb-pipeline` describes.{% endif %}
