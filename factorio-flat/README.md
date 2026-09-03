# Factorio Flat design note

Factorio Flat follows this repository's pack-local README convention and records
design rationale, not copied prompt text.

- OpenAI describes an agent as instructions plus tools and recommends separate
  agents when independent work has complex instructions or tool surfaces, while
  keeping multi-agent use selective. Factorio Flat therefore keeps a small root
  identity, explicit tool ownership, and specialist-specific prompts.
  [OpenAI, Building agents](https://developers.openai.com/tracks/building-agents#orchestration)
- Anthropic distinguishes open-ended agents from fixed workflows, recommends
  parallel work for independent concerns, and uses orchestrator-workers when the
  subtasks must be chosen dynamically. Factorio Flat puts those decisions in an
  on-demand coordination skill instead of an always-on sequence.
  [Anthropic, Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- Google recommends direct, structured instructions, decomposition of complex
  prompts, and aggregation of independent tasks. Factorio Flat uses small skill
  entrypoints with bundled references for progressive disclosure.
  [Google, Gemini prompt design strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies)

Behavior is assessed outside the prompt through normalized public responses and
tool traces. The eval cases test semantic routing, clarification quality,
parallelism, and task continuity without matching exact prose.

## Runtime contract

`ask_user` and `create_a2ui_surface` are explicit runtime tool dependencies for
the experts that declare them. The runtime must expose those names during pack
validation and execution, including on child experts. `create_artifact` remains
an auto-attached ReAct lifecycle tool, so the pack uses it from the dossier skill
without adding it to curated expert allowlists.
