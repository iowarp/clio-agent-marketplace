---
name: use-marimo
title: Use a marimo notebook
description: Use to open, build or explore a marimo notebook with the person - start its server, show it in the shared browser, and run code in its live kernel or add and run cells through marimo-pair.
keywords:
- marimo
- notebook
- reactive notebook
- python notebook
---

# Use a marimo notebook

marimo notebooks are Python files whose cells rerun when what they depend on changes. A
running notebook has a server, a kernel for each open notebook page, and the page the
person reads. marimo's own agent interface works in that same kernel; the `marimo-pair`
skill in this plugin documents it and carries its scripts.

## Server, page and kernel

- **The notebook file.** The person may name one. `marimo edit` on a name that does not
  exist yet starts an empty notebook in the workspace. A file that starts with a
  `# /// script` header is covered under `--sandbox` below.
- **The server** runs in the background with `shell_bash` and `background=true`, bound to
  this computer only, on a free port:

  ```bash
  "$CLIO_UV" run --no-project --python "$CLIO_PYTHON" --with "marimo>=0.21.1" \
    marimo edit NOTEBOOK.py --headless --host 127.0.0.1 -p PORT --no-token --skip-update-check
  ```

  `CLIO_UV` and `CLIO_PYTHON` are the uv and the Python CLIO brings with it, so this
  works on a computer with neither installed, and the notebook runs on the interpreter
  `run_code` uses, with the same packages your scripts have. uv adds marimo in a layer
  of CLIO's own cache; nothing is installed into the person's environments or into
  CLIO's. For a notebook with its own `# /// script` header, `--sandbox` in the
  `marimo edit` arguments makes marimo build the environment the header declares, with
  the `uv` it finds on `PATH`; a `PATH="$(dirname "$CLIO_UV"):$PATH"` prefix on the
  command makes that CLIO's.

  The shell waits for every process a command leaves running, so a server started with
  `&` or `nohup` inside an ordinary command keeps that command, and the turn, waiting;
  `background=true` returns a task handle and leaves the server running. The server is
  up once `curl -sf http://127.0.0.1:PORT/api/sessions` answers.
- **The page** opens in the shared browser from `run_code`:
  `page = await browser.open("http://127.0.0.1:PORT/")`. Opening the page is what starts
  the notebook's kernel session, and the person sees it in the Browser tab. Without the
  browser, the person can open the address themselves.
- **The kernel** is reached through marimo-pair's scripts, run from its skill directory
  with `--url http://127.0.0.1:PORT`; the skill describes the `help(cm)` inspection its
  interface expects first. Scratchpad code reads the live notebook; lasting changes go
  through `marimo._code_mode`, since edits to the `.py` file while it runs are not what
  the kernel holds.

## Where results show

marimo draws tables and charts in widgets whose text a page snapshot does not include,
and it scrolls inside its own panel, so a page screenshot shows only the top of the
notebook. Cell status, errors and values are readable through marimo-pair. An output as
the person sees it comes from scrolling it into view and screenshotting that element:
`out = page.get_by_text("A HEADING OR LABEL NEAR IT")`,
`await out.scroll_into_view_if_needed()`, `path = await out.screenshot()`, then
`view_image` on `path`. A second page joins the notebook as a reader, so the page you
opened is the one to use. A result saying `person_acted` means the person changed
something in the notebook, so earlier reads may be out of date.

A chart, a layout or anything judged by eye is easiest to improve from the screenshot
of its output after each change made through marimo-pair; the image shows what the
next change needs to fix.

The server keeps running between turns until its background task is cancelled, which
fits when the person is done with it or asks.
