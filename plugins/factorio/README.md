# Factorio design note

Factorio (`agents/factorio.py`) is a research partner for scientists who study
how a part's design, material and manufacturing route set its performance.
This note records design rationale, not copied prompt text. The marketplace
rules it follows are in `ARCHITECTURE.md`.

## Composition and levels

`Factorio(ScienceAgent)` selects, beyond the science base (which already
carries the L0 `scientific-method` plugin):

| Plugin | Level | Holds |
| --- | --- | --- |
| `manufacturing` (pack) | L1 | `materials`, `manufacturing-processes`, `characterization`, `mechanical-testing`, `fatigue`, `fea-methods`: method only, no program |
| `abaqus` | L2 | Abaqus scripting and runs, Tosca, result visualization, the `abaqus-topology` views, `abaqus_engineer` |
| `morphorm` | L2 | the Morphorm workflow and its bundled checks |
| `slurm` | L2 | Slurm batch jobs and the bounded-wait helper |
| `factorio` | agent | identity and process: mission, specialist roster, practice; coordination, framing, study-log, audit and evidence fan-out skills; research-process subagents |

No program is the default. Each program plugin has a capabilities fragment
that says what the program can do; the mission tells Factorio to work in
whichever program the scientist uses, and to run meshing, solves and batch
jobs itself when the program is reachable.

## Main-only fragments

CLIO gives a subagent its owner plugin's fragments. `factorio.mission`,
`factorio.practice` and `factorio.specialists` are written for the main
agent, so each is gated on `spawn_skill_task`, a delegation tool the main
agent has and no Factorio subagent is given (every subagent here has a tool
allowlist that omits it). The fragments sort by file name, so `mission.md`
comes first among Factorio's domain fragments.

## Specialists

Each domain specialist lives with the L1 plugin whose skills it uses and
declares every plugin whose skills its prompt or those skills reference:
`materials_scientist` (materials), `manufacturing_expert`
(manufacturing-processes), `characterization_expert` (characterization),
`mechanical_testing_expert` (mechanical-testing), `fatigue_failure_expert`
(fatigue), and `abaqus_engineer` (abaqus). Statistics and figures for a result
set go to a copy of the coordinator, which carries the scientific-method skills.
Every subagent can read and list files; the ones whose job is to
compute or build (characterization, testing, fatigue, the
Abaqus engineer, the simulation methodologist) can also write files and run
the shell. `evidence_leaf` and `evidence_critic` are lanes of
`evidence_researcher`; CLIO has no children-only flag (`internal` hides a
subagent from every agent, its parent included), so they stay delegable and
their descriptions say who starts them.

## Sources

- OpenAI describes an agent as instructions plus tools and recommends separate
  agents when independent work has complex instructions or tool surfaces,
  while keeping multi-agent use selective.
  [OpenAI, Building agents](https://developers.openai.com/tracks/building-agents#orchestration)
- Anthropic distinguishes open-ended agents from fixed workflows, recommends
  parallel work for independent concerns, and uses orchestrator-workers when
  the subtasks must be chosen dynamically. Factorio puts those decisions in an
  on-demand coordination skill instead of an always-on sequence.
  [Anthropic, Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- Google recommends direct, structured instructions, decomposition of complex
  prompts, and aggregation of independent tasks. Factorio uses small skill
  entrypoints with bundled references for progressive disclosure.
  [Google, Gemini prompt design strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies)

Behavior is assessed outside the prompt through normalized public responses
and tool traces (`evals/`). The cases test semantic routing, clarification
quality, parallelism and task continuity without matching exact prose.

## Views

`abaqus-topology` (in `abaqus/ai.iowarp.clio/a2ui/`) holds two topology
optimization views: before and after in linked 3D viewports with a stress
toggle, and the design history with density and cycle sliders. It adds no
rendering of its own: `TopologyViewport` aliases the generic
`clio.mesh-viewport.v1` kernel, `ParameterSlider` the generic
`clio.slider.v1`, and `ConvergencePlot` the generic `clio.chart.v1`. Its
examples are placeholders filled from the run at hand.

## Open work

Most L1 skills are short checklists and should gain procedures, references
and bundled scripts with the domain owners. The `tosca` skill does not
reproduce `.par` syntax: no sourced copy was available, so it tells the agent
to read the installed documentation.
