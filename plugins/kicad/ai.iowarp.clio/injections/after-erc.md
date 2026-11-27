---
name: after-erc
event: tool_result
tool: kicad_run_erc
title: Review the schematic in the schematic view
description: After ERC, tell the agent to look at the schematic in the schematic view and fix what is wrong with the schematic tools.
active: true
---
{% if not tool.is_error %}ERC does not show a wire to the wrong pin or a label on the wrong net; the schematic view does. Look at what you changed in `view_schematic` (open it if it is not open): `focus` on the symbols you edited and look with its `capture` (or `look_at_view`). Fix what is wrong by hand: `sch_delete_wire` and `sch_route_wire_between_pins` or `sch_add_wire`, `sch_move_symbol`, `sch_modify_label`.{% endif %}
