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
person reads. You work in that same kernel through marimo's own agent interface, the
`marimo-pair` skill in this plugin: load it before you touch the notebook, and follow it.

## Start, show, pair

1. **The notebook.** Use the file the person names. For a new one, pick a file name in the
   workspace: `marimo edit` on a name that does not exist yet starts an empty notebook. If
   the file starts with a `# /// script` header, add `--sandbox` to the command below.
2. **Start the server in the background** with `shell_bash` and `background=true`, bound to
   this computer only, on a free port:

   ```bash
   uvx --from "marimo>=0.21.1" marimo edit NOTEBOOK.py --headless --host 127.0.0.1 \
     -p PORT --no-token --skip-update-check
   ```

   The shell waits for every process a command leaves running, so a server started with
   `&` or `nohup` inside an ordinary command keeps that command, and the turn, waiting;
   `background=true` returns a task handle and leaves the server running. `uvx` runs
   marimo without changing the workspace's environment; when that environment already has
   marimo (`uv run marimo --version` answers), `uv run marimo ...` uses it. Wait until
   `curl -sf http://127.0.0.1:PORT/api/sessions` answers.
3. **Open it in the shared browser** from `run_code`:
   `page = await browser.open("http://127.0.0.1:PORT/")`. Opening the page is what starts
   the notebook's kernel session; tell the person it is in the Browser tab. Without the
   browser, give the person the address to open.
4. **Pair with marimo-pair.** Load the `marimo-pair` skill and run its scripts from its
   skill directory with `--url http://127.0.0.1:PORT`: first the `help(cm)` inspection it
   requires, then your code. Scratchpad code reads the live notebook; changes that should
   last go through `marimo._code_mode`, not edits to the `.py` file while it runs.
5. **Check results in the kernel, look in the page.** marimo draws tables and charts in
   widgets whose text a page snapshot does not include, and it scrolls inside its own
   panel, so a page screenshot shows only the top of the notebook. Read cell status,
   errors and values through marimo-pair. To see an output as the person does, scroll it
   into view and screenshot that element: `out = page.get_by_text("A HEADING OR LABEL
   NEAR IT")`, `await out.scroll_into_view_if_needed()`, `path = await out.screenshot()`,
   then look at `path` with `view_image`. Use the page you opened; a second page joins
   the notebook as a reader. When a result says `person_acted`, the person changed
   something in the notebook; read it again.
6. **Review visual work by looking at it.** For a chart, a layout or anything judged by
   eye, work in rounds: change the cell through marimo-pair, let it run, screenshot the
   output, look at it, and decide the next change from what you saw. Say what you saw and
   what you changed in each round.
7. **Stop the server** (cancel its background task) when the person is done with it or
   asks; until then it keeps running between turns.
