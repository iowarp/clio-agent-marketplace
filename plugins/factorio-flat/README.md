# Factorio Flat design note

Factorio Flat (`agents/factorio.py`, the `factorio-flat` plugin over the
`manufacturing` pack) records design rationale here, not copied prompt text.

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

## Layout

The agent is `FactorioFlat(ScienceAgent)`: the science base plus the
`manufacturing` pack and this plugin.

- This plugin holds the root's domain fragments and the research-process
  subagents: `research_methodologist`, `virtual_lab`, `evidence_researcher`
  (which delegates to `evidence_leaf` and `evidence_critic`, the one two-level
  fan-out), `simulation_methodologist`, `abaqus_engineer` and
  `independent_reviewer`.
- The `manufacturing` pack's member plugins hold the specialized knowledge as
  skills, and each specialist subagent lives with its member:
  `materials` (`materials_scientist`), `am-process` (`manufacturing_expert`),
  `characterization` (`characterization_expert`), `mechanical-testing`
  (`mechanical_testing_expert`), `fatigue` (`fatigue_failure_expert`) and
  `scientific-method` (`data_analysis_expert`, plus the coordination,
  formulation, dossier, audit, evidence and literature skills). `abaqus` holds
  the Abaqus, FEA and visualization skills; `topology` holds the Tosca,
  Morphorm and topology optimization skills and the `abaqus-topology` A2UI
  catalog.

A skill can serve more than one subagent (for example `heat-treatment`, in
`materials`, is used by both `materials_scientist` and `manufacturing_expert`):
each subagent lists the plugins whose skills and tools it needs.

## Views

`abaqus-topology` (in `topology/ai.iowarp.clio/a2ui/`) holds two topology
optimization views: before and after in linked 3D viewports with a stress
toggle, and the design history with density and cycle sliders. It adds no
rendering of its own: `TopologyViewport` aliases the generic
`clio.mesh-viewport.v1` kernel, `ParameterSlider` the generic `clio.slider.v1`,
and `ConvergencePlot` the generic `clio.chart.v1`, bound to the viewport's
threshold and frame. The `abaqus-visualization` skill ships the exporter
(`odb_to_glb.py`, `fea_glb.py`) that turns ODB, `.inp`, and Tosca STL output
into the `.glb` meshes the viewport reads, plus `render_view.py` for report
figures; `visualize-topology-optimization` builds the two views on top of it.
`create_artifact` comes from the core plugin, so a skill can use it for durable
deliverables without adding it to a subagent's tool allowlist.

The skill roster is a first-pass, intentionally granular set rather than a
merged one; expect it to be pruned and consolidated as it sees use.
