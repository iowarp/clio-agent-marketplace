# Contributing

## Pack policy checks

CI runs these checks over every pack at the repository root (`old/`,
`scripts/`, `tests/` and hidden directories are not packs):

```sh
uv run --no-project python -m unittest discover -s tests
uv run --no-project python scripts/check_model_pins.py .
uv run --no-project python scripts/check_skill_literals.py .
```

### No dataset facts in skills

Skills and experts carry checks, not facts about one dataset or experiment.
A station id, a row count, or a measured ratio ("values are ~40× too small")
copied from a run the pack was tuned on is L3 leakage: the agent then asserts
it for every other dataset.

`check_skill_literals.py` scans each pack's `AGENT.md` body, `experts/*.md`,
and every text file under `skills/` (SKILL.md, bundled scripts and
references). It skips the pack's `tests/`, `evals/` and `fixtures/`
directories.

- `<pack>/lint-denylist.txt`: one literal per line, `#` comment lines. Any
  occurrence is an error. Add the ids and numbers from the data you tuned on.
- `<pack>/.lint-l3`: an empty marker file that opts the pack into the generic
  rules: ISO dates, measured magnitudes (`~40×`, `40x too`, `30–50×`), sample
  keys (`12__345__678`), and concrete dataset file names with a digit
  (`P475.CI.LY_.20.csv`; templated names such as `<station>.csv` pass). New
  packs should add it. Try it on a pack without the marker with
  `--strict-pack NAME`.
- A line containing `lint: allow-literal` is exempt, for a deliberate example.

Findings print as `path:line: rule: excerpt`, and the script exits 1.
