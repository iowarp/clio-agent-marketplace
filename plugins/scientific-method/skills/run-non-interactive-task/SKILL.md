---
name: run-non-interactive-task
title: Run a Self-Contained Task With No One to Ask
description: Use when working through a self-contained task packet (workspace rules, required outputs and paths) with no person available during the run.
keywords:
- level:L0
- workflow
- batch
---

A task is non-interactive when it arrives as a self-contained packet: a
problem statement, workspace rules, a list of required outputs at required
paths, and no person available to answer during the run (a trial or pilot
prompt, a frozen configuration with a deliverables list, a scheduled job).
Interactive work is unchanged by this skill.

## What the packet defines

- The packet's required outputs are the deliverables. Specialists, planning and
  presentation bookkeeping it does not ask for add steps and context without
  adding to them.
- Nobody reads progress narration during the run; independent tool calls in one
  step finish sooner than the same calls one by one.
- The packet's file list and its toolchain (the program's skill, the
  scheduler's skill) are what the first step can take in together.

## Manuals

A PDF manual converted to text once in the work directory (for example with
`pdftotext -layout`) can be searched (`grep -n`) and printed by section
(`sed -n`); paging through the whole text fills the context. Keywords from
memory are often wrong; the manual is the reference.

## Verification

The loaded skills' bundled checks, with their output saved, are the
verification record; a new verification program is needed only for a check
they cannot do.

## A facts log and the reports

- A short facts log in the work directory (for example `work/notes.log`), one
  line per event (a timestamp, the command, its exit code, a job id or a key
  value), is what reports are written from.
- A required report (for example a run summary) written once near the end from
  that log carries every item the packet's provenance requirements list. Long
  material (hash manifests, logs, generated files) is referenced by path unless
  the requirements ask for it inline.

## Tool-call size

- Commands go to the shell as JSON strings: a line break inside a string is
  `\n`, a tab `\t`, a double quote `\"` and a backslash `\\`. A raw line break
  inside a JSON string, including in heredocs, breaks the call.
- The shell tool limits the length of one command; its description states the
  limit in effect (CLIO's default is 16,000 characters, and sites can change
  it), and native shells can reject shorter ones. Programs fit better in script
  files than in long inline commands. A long file can be written in parts
  (`part1.md`, `part2.md`, ...) in one parallel step and joined in the next
  (`cat part*.md > file`).
- A patch (`sed -i`, a small script) or an append (`cat >>`) changes a few lines
  without re-sending the whole file; the same file content sent twice is wasted
  context.

A run is complete when every required output exists at its required path.
