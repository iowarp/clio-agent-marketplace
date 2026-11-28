---
name: after-sync
event: tool_result
tool: kicad_pcb_sync_from_schematic
title: Placement shows best in the board view
description: When the board is synced from the schematic, suggest judging placement in the board view.
active: true
---
{% if not tool.is_error %}The footprints are on the board now; the board view (`view_board`, with `set_layers` to the courtyards and Edge.Cuts and `focus` on the parts) shows a placement better than the numbers alone.{% endif %}
