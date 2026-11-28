---
name: after-autoroute
event: tool_result
tool: kicad_route_*
title: The autorouted tracks are worth a look
description: After FreeRouting or an imported routed session, suggest reviewing the routes visually in the board view.
active: true
---
{% if not tool.is_error and tool.name in ["kicad_route_autoroute_freerouting", "kicad_route_import_ses"] %}The autorouter connected the nets without judging them, so the routes are worth a look in the board view (`view_board`, with `set_layers` and `focus` on the power nets, decoupling, differential pairs and dense areas). Its usual faults are narrow power tracks, wandering decoupling loops, split pairs, copper in a keepout, detours, needless vias and stubs; `pcb-routing` has the tools to fix them by hand.{% endif %}
