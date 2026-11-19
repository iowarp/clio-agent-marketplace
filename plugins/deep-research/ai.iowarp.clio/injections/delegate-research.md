---
name: delegate-research
event: tool_result
tool: search_tools
title: Suggest cheaper researchers for a large exploration
description: When the agent loads run_flow, remind it that a large deep-research exploration can run its researchers on a smaller model and keep the critic on its own model.
active: true
---
{% if "run_flow" in (tool.args.query or "") and not tool.is_error %}Before you start deep research: an exploration with many independent directions can run its researchers on a smaller, cheaper model (the `researcher_model` option) while the critic stays on your model; `list_models` marks fast models. A narrow question needs neither.{% endif %}
