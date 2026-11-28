---
name: start-a-paper
description: Use when starting a new LaTeX paper for a venue (IEEE, ACM, Springer LNCS, Elsevier) or turning a draft into one - the shipped templates, their venue rules and how they build.
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

- The template follows from the venue the person names; with no venue named, the venue is the person's to say. An existing draft's `\documentclass` and options identify its template.
- A template copied into a folder of the workspace keeps `main.tex` as the entry; it `\input`s the files under `sections/`.
- The `rules` in `template.yaml` are that kind of venue's usual defaults. A call for papers sets the real `page_limit`, `references_count` and `double_blind`, which go in the copy.
- The paper is shown by its `\title`. `latex_build(entry, venue=<template name>)` builds it and names every problem by file and line. The build makes the paper, shown by its title with its type and venue from `template.yaml`.
- Figures go under `figs/`; a figure a script draws is made by the script, so changing the figure means changing and rerunning the script. A figure registered with `create_artifact(path=<figure>, used=[<script>, <data>])` after the script runs carries its producer, so a comment on the figure names the script that made it.
