# Contributing

## Layout

This marketplace uses the native Agent Plugins 1.0.0 format with CLIO's
`ai.iowarp.clio` namespace (see clio-agent's
`docs/design/sdk/plugins-and-composition.md` and `agent-sdk.md`):

- `ai.iowarp.clio/marketplace.json` names the marketplace (`clio`).
- `plugins/<id>/` is one plugin: `plugin.json`, portable `skills/<name>/SKILL.md`
  (the `name` equals the folder: lowercase letters, digits and hyphens) and
  `mcp.json`, plus `ai.iowarp.clio/` for CLIO parts: `tools/` (built-in tool
  claims), `prompt/` (fragments with `id: <plugin>.<name>` and a `section`;
  files without a section are plain prompts such as `prompt/subagents/<id>.md`),
  `subagents/`, `hooks/` and `a2ui/<catalog>/`. MCP launchers reference the
  plugin folder as `${PLUGIN_ROOT}`.
- `agents/*.py` holds one Python class per agent (`clio_agent.sdk.Agent`, or
  `StandardAgent`/`ScienceAgent` from `agents/standard.py`). An agent owns only
  its identity (`id`, `version`, `name`, `role`, `description`) and its plugin
  list, which always extends a parent's list so it carries `core`.

Put a capability in the plugin that owns it and depend on shared plugins
(`workspace`, `shell`, `web`, `pdf`, `documents`, `visuals`, `delegation`, the
clio-kit server plugins such as `pandas` or `ndp`, ...) instead of copying their
skills or redeclaring their servers: a tool, skill, server or subagent name
exposed by two plugins of one agent is a resolution error.

## Checks

CI runs the dependency-free policy checks:

```sh
uv run --no-project python -m unittest discover -s tests
uv run --no-project python scripts/check_model_pins.py .
uv run --no-project python scripts/check_skill_literals.py .
```

and the install resolver plus each plugin's own tests, with clio-agent:

```sh
clio-agent plugin check .
pytest plugins/*/tests
```

### No unjustified model pins

Agents and subagents inherit the session's provider and model.
`check_model_pins.py` reports any `Prefers(model=...)` or `Prefers(provider=...)`
in `agents/*.py` or plugin Python, and any `prefers` in a plugin.json extension,
unless an adjacent `# model-pin-justification: <reason>` comment explains it.

### No dataset facts in skills

Skills and prompts carry checks, not facts about one dataset or experiment.
A station id, a row count, or a measured ratio ("values are ~40× too small")
copied from a run the plugin was tuned on is L3 leakage: the agent then asserts
it for every other dataset.

`check_skill_literals.py` scans each plugin's `ai.iowarp.clio/prompt/` Markdown
(fragment bodies and subagent prompts) and every text file under `skills/`
(SKILL.md, bundled scripts and references). It skips `tests/`, `evals/` and
`fixtures/` directories.

- `plugins/<id>/lint-denylist.txt`: one literal per line, `#` comment lines.
  Any occurrence is an error. Add the ids and numbers from the data you tuned on.
- `plugins/<id>/.lint-l3`: an empty marker file that opts the plugin into the
  generic rules: ISO dates, measured magnitudes (`~40×`, `40x too`, `30–50×`),
  sample keys (`12__345__678`), and concrete dataset file names with a digit
  (`P475.CI.LY_.20.csv`; templated names such as `<station>.csv` pass). New
  domain plugins should add it. Try it on a plugin without the marker with
  `--strict-pack NAME`.
- A line containing `lint: allow-literal` is exempt, for a deliberate example.

Findings print as `path:line: rule: excerpt`, and the script exits 1.
