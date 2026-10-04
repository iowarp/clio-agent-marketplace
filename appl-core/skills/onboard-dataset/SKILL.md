---
name: onboard-dataset
title: Onboard a Dataset
description: First contact with any tabular dataset directory - read its self-description, inventory it, audit columns/keys/flags with bundled scripts, record facts and traps in an experiment card, save a loader, and produce validated views. Use before analysing a dataset that has no current experiment card.
keywords:
- level:L0
- data-onboarding
- data-quality
- experiment-card
---

# Onboard a dataset

Goal: turn an unfamiliar dataset directory (the *bundle root*) into three
artefacts, stored in the **active workspace** so that no later session has to
profile it again:

| Artefact | Path | Content |
| --- | --- | --- |
| experiment card | `<workspace_state>/datasets/<key>/experiment-card.md` | facts tagged stated/checked/inferred, traps, open questions, proposed lessons, loader and view hashes |
| loader | `<workspace_state>/datasets/<key>/loader.py` | one idempotent script that reads the raw files and applies every decision in the card |
| views | `<workspace_state>/datasets/<key>/views/` | analysis-ready tables written by the loader (Parquet) |

Audit reports go to `<workspace_state>/datasets/<key>/audit/`. Call this
directory `DATASET_DIR`; `card.py status` prints it (`dataset_dir:`).

- **Default location: Agent workspace state.** CLIO's shell supplies the absolute
  `CLIO_AGENT_WORKSPACE_STATE_DIR` from its canonical resolver on the execution host.
  Run `card.py` without `--store`; it uses this value, independent of the command's
  working directory. The returned `dataset_dir` is authoritative. A standalone
  invocation requires an explicit absolute `--store` state directory. Never guess
  a home directory or recreate workspace `.clio`; report missing configuration.
  Keep old `.clio` cards untouched until the user explicitly migrates them.
  Permissions remain CLIO's decision: report denied writes plainly.
- **Analysis hygiene.** Do not change raw data values in place; every
  cleaning decision lives in the loader and views and is recorded in the card.
- `<key>` is the first 16 hex characters of the SHA-256 of the export's
  manifest file, so a second session, or the same export at a different path,
  finds the same card by recomputing the key. Without a manifest the key is
  built the same way from the resolved absolute bundle path (it changes if the data
  moves). The card's frontmatter records the absolute bundle path, the
  manifest's SHA-256, and `export_version`.

This skill deepens the generic `inspect_dataset_structure` and
`reason_about_quality` procedures of the Data Semantics pack: same intent,
but every check here has a script and ends up in the card.

## Running the bundled scripts

`load_skill` reported this skill's directory as `SKILL_ROOT`; substitute that
literal path in the commands below. Run through uv's shared cache, never a
`.venv` inside the skill directory. The commands work on Windows and Linux.

```text
uv run --no-project python "SKILL_ROOT/scripts/card.py" status|init|record|verify BUNDLE_ROOT
uv run --no-project --with "pyarrow>=15" python "SKILL_ROOT/scripts/inventory.py" BUNDLE_ROOT --out DATASET_DIR/audit/inventory.json
uv run --no-project --with "pyarrow>=15" --with "numpy>=1.24" python "SKILL_ROOT/scripts/audit_columns.py" TABLE --out DATASET_DIR/audit/columns-NAME.json
uv run --no-project --with "pyarrow>=15" python "SKILL_ROOT/scripts/join_keys.py" TABLE_A TABLE_B --keys K1,K2 --out DATASET_DIR/audit/join-NAME.json
uv run --no-project --with "pyarrow>=15" python "SKILL_ROOT/scripts/flag_check.py" TABLE --flags FLAG_COL --signal SIGNAL_COL --out DATASET_DIR/audit/flags-NAME.json
```

The audit scripts only read their inputs. Each prints a short summary and
writes the full JSON to `--out` (always a path under `DATASET_DIR/audit/`,
never under the bundle root). Without `--out` the JSON follows the summary
on stdout, which can exceed the shell output cap on wide tables; prefer
`--out` and read the JSON with `fs_read_file` only where the summary points. Prefer Parquet over a CSV twin
of the same table: it is smaller and keeps types. `audit_columns.py --sample N`
reads only the first N rows; a finding from a sample is `[checked]` for the
sample only, so say so.

## Procedure

1. **Is there already a card?** Run
   `card.py status BUNDLE_ROOT ` and note `dataset_dir`.
   - `state: current` and `hashes: match`: reuse the card. Read it, run the
     loader once (step 8) and continue with the analysis. Do not re-profile.
   - `state: stale` (the store has a card for this bundle path made from a
     different manifest, listed under `previous_cards`) or `hashes: drift`:
     the data or the loader changed since the card was written. For a stale
     card, `init` a new one and carry over only what you re-check; re-run
     only the audits whose tables changed, and say what changed.
   - `no_card`: continue.
2. **Read the self-description before any profiling.** In this order: a
   manifest (`manifest.json` or similar), README files, documentation folders,
   column catalogs / data dictionaries / codebooks, and any machine-readable
   blocks inside the docs (YAML or JSON front matter). Record what they
   *state* (identity, version, table list, units, definitions, warnings) as
   `[stated]` with the source file. If the export declares a format or version
   and a loaded skill says which versions are supported, check it now and stop
   on an unsupported one.
3. **Inventory.** Run `inventory.py`. Note table sizes, row counts, schemas,
   twins (the same table as CSV and Parquet), docs, and every
   `declared_counts` status other than `match`, every file the manifest
   references that is missing, and tables it does not reference.
4. **Create the card** with `card.py init BUNDLE_ROOT `,
   then fill it as you go
   (see `evidence-and-claims` for tagging). Never overwrite an existing card
   without `--force` and a reason.
5. **Audit the tables** that matter for the questions at hand (all of them on
   a first full onboarding; start with the smallest of each kind, then the
   long/wide measurement tables): `audit_columns.py` per table,
   `join_keys.py` for every join you intend to make, `flag_check.py` for every
   QC/flag column against the signal it is supposed to describe. Work through
   the checklist below; each confirmed problem becomes one
   `- [trap:<class>] ...` line in the card.
6. **Decide, per trap, what the loader does** (drop, null-out, choose one
   source, rename, keep with a caveat) and write the decision on the trap's
   line. Anything whose meaning you cannot establish from the files goes to
   *Open questions for data owners* -- ask the user rather than guess (a
   treatment's meaning, a unit that looks wrong, whether zeros are real).
7. **Write the loader** `DATASET_DIR/loader.py`: a PEP 723 script
   (`# /// script` block with pinned dependencies) that takes the bundle root
   as its first argument, discovers files from the manifest (not hard-coded
   lists), applies the card's decisions, and writes the views to
   `Path(__file__).parent / "views"`. Make it deterministic: sort rows by the
   view's key, fix column order, no timestamps or random ids in outputs,
   overwrite its own outputs. It writes only to its own directory and leaves
   the raw files as they are.
8. **Run the loader, validate, record.** Run it with `uv run --no-project
   DATASET_DIR/loader.py BUNDLE_ROOT` (or with `--with` flags), validate the views
   (the `phenotyping-onboarding-checks` skill has schemas and a validator for
   phenotyping data), check row counts after every join, then
   `card.py record BUNDLE_ROOT `. Run the loader a
   second time and `card.py verify BUNDLE_ROOT `:
   identical hashes prove it is deterministic.
   If they differ, fix the loader before anyone trusts a view.
9. **Report** in a few lines: what the dataset is, the traps found and how
   they are handled, the open questions, and the card/loader/view paths.

## Checklist (phrased as checks; apply to every table)

**Missing-value encodings**
- Check numeric columns for sentinel codes: values at or near the float
  maximum (|x| >= 1e300), the float32 maximum, and codes such as -9999, -999,
  9999. A value repeated exactly many times far outside the bulk is a code,
  not a measurement. Null it in the loader.
- Check for impossible zeros: zeros in a column that is otherwise strictly
  positive (sizes, weights, counts of a present object) may mean "not
  measured". Check whether zeros coincide with other signs of absence.
- Check string columns for empty strings and whitespace; an empty string is a
  missing value that a null count does not see.

**Empty and duplicated columns**
- Check for all-empty columns, especially string-typed columns whose
  non-empty fraction is zero ("ghost" columns). They often sit next to a real
  numeric twin.
- Check for near-duplicate names that differ only by rounding of an embedded
  number (for example two wavelength labels 0.01 apart) or by case and
  punctuation. Keep the populated, correctly typed member; record the pair.
- Check for columns with identical content under different names (factor
  columns repeated) and pick one canonical name.

**Flags versus data**
- Check that each QC flag agrees with the data it describes (`flag_check.py`).
  A flag on (almost) every row is noise, not a filter. Flags can also miss real
  problems: count rows with no signal that carry no specific flag. Filter on
  the signal itself when the flags do not track it.
- Check that an issues/QC table that claims "no problems" is consistent with
  what the audits found; an empty issue log is not evidence of clean data.

**Keys and joins**
- Check key formats across tables before joining: case, separators, number of
  components, prefix/suffix tokens, and storage type ('1' is not 1). Where a
  combined key string does not match, join on its component columns instead.
- Check key uniqueness on both sides; many-to-many joins multiply rows.
- After every join, compare row counts before and after and against the
  number of expected units x times. Use outer joins deliberately and count the
  unmatched rows on each side.

**Units and physical plausibility**
- Check that units (declared, or implied by name suffixes) give physically
  plausible magnitudes: object sizes against the documented frame or
  container size, ratios within their possible range, values of the same
  quantity from two instruments against each other. A disagreement by a large
  factor is a unit or calibration problem until shown otherwise; ask.
- Check whether a quantity is absolute or relative (arbitrary units, vendor
  ratios, indices with non-standard formulas) before comparing across
  instruments or datasets.

**Signals over time**
- Check growth-like signals for saturation or clipping: a plateau that
  coincides with objects touching the edge of their crop or frame, or with a
  sensor's maximum, is a measurement limit, not biology.
- Check sampling: gaps, split or aborted sessions, sessions with fewer units
  than usual, and several observations per unit per period. Choose an
  aggregation (one fixed session per period, or a daily summary) before
  comparing sensors or computing rates, and record it.
- Check the same quantity delivered by two sources or methods (vendor value vs
  recomputed value); they can disagree. Pick one consistently and say which.

**Design**
- Check design balance: count units per factor combination; note empty or
  unequal cells.
- Check factor encoding: is a treatment a numeric dose or a category? Are
  labels consistent (spelling, case)? Is the same factor stored in several
  columns, or also encoded inside another label?
- Check that the design table and the measurement tables cover the same
  units, and which units are missing from which sensor.

**Structure**
- Check for lists or JSON stored inside string cells and parse them once in
  the loader.
- Check dates/times stored as strings, their timezone (usually unstated --
  record the assumption), and numbers stored as strings.
- Check declared counts and table lists (manifest, docs) against the files:
  missing tables, stale extra files, row-count mismatches.

## Trap classes for the card

Tag each trap line with exactly one class so later sessions and graders can
read the card: `sentinel-values`, `ghost-columns`, `near-duplicate-columns`,
`unflagged-missing`, `universal-flag`, `key-format-mismatch`,
`declared-vs-actual`, `unit-scale-suspect`, `saturation-clipping`,
`irregular-sampling`, `design-encoding`, `duplicate-measures`,
`impossible-values`, `list-in-string`, `label-inconsistency`.

## Proposed lessons

When you find something the checklist above did not make you look for, add a
line under *Proposed lessons* phrased as a check that would apply to any
dataset ("check whether ..."). Do not edit skills; lessons are promoted by
people after a second dataset shows the same problem.
