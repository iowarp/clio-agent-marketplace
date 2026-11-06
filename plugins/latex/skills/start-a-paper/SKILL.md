---
name: start-a-paper
description: Use when starting a new LaTeX paper for a venue (IEEE, ACM, Springer LNCS, Elsevier) or turning a draft into one - pick the template, copy it into the workspace, fill it in and build early.
---

# Start a paper from a template

The templates are in this plugin's `templates` folder, beside this skill's `skills`
folder (`../../templates/<name>/` from here). Each has a `template.yaml` with its class,
options and venue rules, a `main.tex`, `sections/body.tex` and a `refs.bib`.

| Template | Class and options |
| --- | --- |
| `ieee-conference` | `IEEEtran`, `conference` |
| `ieee-journal` | `IEEEtran`, `journal` |
| `acm-sigconf` | `acmart`, `sigconf,review,anonymous` (double-blind review) |
| `acm-journal` | `acmart`, `acmsmall` |
| `springer-lncs` | `llncs` |
| `elsevier` | `elsarticle` |

1. Pick the template from the venue the person names. When they name none, ask. For an existing draft, pick it from the draft's `\documentclass` and options.
2. Copy the template's files into a folder of the workspace, keeping `main.tex` as the entry and `sections/` for the body. Put each section in its own file under `sections/` and `\input` it from `main.tex`.
3. The `rules` in `template.yaml` are that kind of venue's usual defaults. When the person gives the call for papers, set `page_limit`, `references_count` and `double_blind` in the copy to match it.
4. Set `\title` early: the paper is shown by it. Build right away with `latex_build(entry, venue=<template name>)`, and after each change. Fix every problem the build names by file and line. The build makes the paper, shown by its title with its type and venue from `template.yaml`.
5. Figures go under `figs/`; a figure a script draws is made by the script, and the script is changed when the figure needs to change. After running the script, register the figure with `create_artifact(path=<figure>, used=[<script>, <data>])`, so a comment on the figure names the script that made it.
