---
name: after-autoroute
event: tool_result
tool: kicad_route_*
title: Review the routes the autorouter made, and fix them by hand
description: After FreeRouting or an imported routed session, tell the agent to look at the routes in the board view, judge them, and correct what is wrong with the hand-routing tools.
active: true
---
{% if not tool.is_error and tool.name in ["kicad_route_autoroute_freerouting", "kicad_route_import_ses"] %}The autorouter connected the nets; it did not judge them. Look at the routes now in the board view (`view_board`; open it if it is not open): `set_layers` to the copper layers, `focus` on the power nets, the decoupling capacitors, the USB pair and any dense area, and look with its `capture` (or `look_at_view`). Check that power tracks are wide enough for their current, decoupling loops stay at their pins, a differential pair runs together, nothing crosses an antenna keepout, and there are no long detours, needless vias, acute angles or stubs. Fix what is wrong by hand: `pcb_delete_items` on the bad tracks, then `route_single_track`, `route_from_pad_to_pad` and `pcb_add_via`, and look again.{% endif %}
