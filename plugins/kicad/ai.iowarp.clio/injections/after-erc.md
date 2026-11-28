---
name: after-erc
event: tool_result
tool: kicad_run_erc
title: The schematic view shows what ERC cannot
description: After ERC, suggest looking at the edited symbols in the schematic view.
active: true
---
{% if not tool.is_error %}ERC does not see a wire on the wrong pin or a label on the wrong net; the schematic view (`view_schematic`, with `focus` on the symbols you edited) shows them.{% endif %}
