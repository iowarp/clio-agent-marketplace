---
name: after-drc
event: tool_result
tool: kicad_run_drc
title: The violations are easier to judge in place
description: After DRC, suggest looking at the violations where they are on the board.
active: true
---
{% if not tool.is_error %}The violations are easier to judge where they are: `view_checks` lists them by rule, and selecting one focuses the board view (`view_board`) on it.{% endif %}
