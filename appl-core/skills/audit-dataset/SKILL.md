---
name: audit-dataset
title: Audit a Dataset in a Child Agent
description: Onboard one dataset bundle root in a fresh child agent (inventory, audits, experiment card, loader, views) and return only the artefact paths, traps, and open questions, keeping the profiling out of the parent's context.
effect: spawn_subagent_with_skill
keywords:
- level:L0
- data-onboarding
- delegation
---

You are already running this skill in the delegated child. Do not call
`load_skill` for this skill, `spawn_skill_task`, or any other delegation tool.
Complete the assignment directly in this child turn.

The assignment must name one bundle root (an absolute directory path) and may
name the questions the parent cares about. Do not infer a bundle root that
was not given; if it is missing or not a readable directory, return that as a
blocker.

By default everything you write goes into the active workspace (given in
your prompt as "Active workspace root: ..."), under
`<workspace_state>/datasets/<key>/`, which keeps the raw export pristine
and lets later sessions find the card. If the assignment names another
location, use it. If clio's permission system denies a write, return that
plainly as a blocker.

1. Load `onboard-dataset` and follow its procedure on the assigned bundle
   root, from `card.py status` to `card.py verify`, passing the active
   workspace root as `` on every `card.py` call and
   writing audit reports under the `dataset_dir` it prints. Load `evidence-and-claims`
   for tagging, and, when the data is plant phenotyping,
   `phenotyping-onboarding-checks` for the view shapes. If the export declares
   a format version, apply the export skill's version check first and stop on
   an unsupported version.
2. Do not ask the user questions from this child. Put every question you
   would have asked under *Open questions for data owners* in the card and
   make the loader take the conservative choice (keep both candidates, flag,
   or exclude with a caveat) until it is answered.
3. Do not create A2UI surfaces. The parent owns presentation.
4. Return exactly this, as short plain text:
   - `card:` absolute path of the experiment card
   - `dataset_dir:` absolute path of `<workspace_state>/datasets/<key>/`
   - `loader:` absolute path of the loader, and the exact command you ran it with
   - `views:` each view path with its SHA-256 as recorded by `card.py record`
   - `verify:` the exact final `card.py verify ... --store ...` command and its
     result (must be exit 0)
   - `traps:` one line per trap, `[trap:<class>] <where> -- <what> -- <handling>`
   - `open questions:` one line each
   - `blockers:` anything you could not do, or `none`

The parent does not trust this report on its own: it re-runs the loader and
compares the view hashes before using the card, so report the command and
hashes exactly as they are on disk.
