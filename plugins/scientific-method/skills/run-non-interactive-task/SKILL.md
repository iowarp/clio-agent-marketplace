---
name: run-non-interactive-task
title: Run a Self-Contained Task With No One to Ask
description: Work through a self-contained task packet (workspace rules, required outputs and paths, no person available during the run) directly and economically - batch independent calls, read manuals once and search them, verify with bundled checks, keep a facts log, write the required reports once, and confirm every required output before stopping.
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

## Work directly

- Do the work yourself. Consult a specialist only when the packet asks for one.
- Skip planning and presentation bookkeeping the packet does not ask for.
- Keep each step's visible text to one short sentence, and batch independent
  tool calls into one step.
- In the first step, read the packet's file list and, in the same step, load
  the skills for its toolchain (the program's skill, the scheduler's skill).

## Read manuals once

Convert each PDF manual to text once in the work directory (for example with
`pdftotext -layout`), then search it (`grep -n`) and print only the sections
you need (`sed -n`). Do not page through the whole text, and confirm every
keyword against the manual rather than memory.

## Verify with what is bundled

Use the bundled checks of the loaded skills and save their output as the
verification record. Write a new verification program only for a check they
cannot do.

## Keep a facts log, write reports once

- Append one line per event to a short facts log in the work directory (for
  example `work/notes.log`): a timestamp, the command, its exit code, a job id
  or a key value.
- Write each required report (for example a run summary) once, near the end,
  from that log. Include every item the packet's provenance requirements list.
  Reference long material (hash manifests, logs, generated files) by path
  unless the requirements ask for it inline.

## Keep tool calls small

- Commands go to the shell as JSON strings: a line break inside a string is
  `\n`, a tab `\t`, a double quote `\"` and a backslash `\\`. Never put a raw
  line break inside a JSON string, including in heredocs.
- The shell tool limits the length of one command; its description states the
  limit in effect (CLIO's default is 16,000 characters, and sites can change
  it), and native shells can reject shorter ones. Put programs in script
  files rather than long inline commands. For a long file, write it in parts
  (`part1.md`, `part2.md`, ...) in one parallel step and join them in the next
  (`cat part*.md > file`).
- Never re-send a whole file to change a few lines: patch it (`sed -i`, a small
  script) or append (`cat >>`). Never emit the same file content twice.

## Before stopping

Check that every required output exists at its required path, then give the
final answer once.
