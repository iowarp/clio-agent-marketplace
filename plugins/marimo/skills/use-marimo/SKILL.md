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
   the file starts with a `# /// script` header, see `--sandbox` below.
2. **Make a token, then start the server in the background.** Anyone who can reach a
   marimo server can run code in its kernel, and every account on this computer can reach
   a port on `127.0.0.1`, so the server always requires a token. First write a new one to
   a file only this user can read, with an ordinary `shell_bash` call that prints the
   file's path:

   ```bash
   TOKEN_FILE=$(umask 077 && mktemp) && \
     "$CLIO_PYTHON" -c 'import secrets; print(secrets.token_urlsafe(24))' > "$TOKEN_FILE" && \
     echo "$TOKEN_FILE"
   ```

   Then start the server with `shell_bash` and `background=true`, bound to this computer
   only, on a free port, with that file as `TOKEN_FILE`:

   ```bash
   "$CLIO_UV" run --no-project --python "$CLIO_PYTHON" --with "marimo>=0.21.1" \
     marimo edit NOTEBOOK.py --headless --host 127.0.0.1 -p PORT \
     --token-password-file TOKEN_FILE --skip-update-check
   ```

   Never start marimo with `--no-token` or `--host 0.0.0.0`, even where marimo-pair's
   reference suggests it for discovery or for WSL: without a token, other accounts on
   this computer can run code as the person, and `0.0.0.0` opens it to the network.

   `CLIO_UV` and `CLIO_PYTHON` are the uv and the Python CLIO brings with it, so this
   works on a computer with neither installed, and the notebook runs on the interpreter
   `run_code` uses, with the same packages your scripts have. uv adds marimo in a layer
   of CLIO's own cache; nothing is installed into the person's environments or into
   CLIO's. For a notebook with its own `# /// script` header, add `--sandbox` to the
   `marimo edit` arguments: marimo then builds the environment the header declares, with
   the `uv` it finds on `PATH`, so start the command with
   `PATH="$(dirname "$CLIO_UV"):$PATH"` to make that CLIO's.

   The shell waits for every process a command leaves running, so a server started with
   `&` or `nohup` inside an ordinary command keeps that command, and the turn, waiting;
   `background=true` returns a task handle and leaves the server running. Wait until
   `curl -sf http://127.0.0.1:PORT/health` answers.
3. **Open it in the shared browser** from `run_code`, with the token read from the file:
   `page = await browser.open(f"http://127.0.0.1:PORT/?access_token={token}")`. Opening
   the page is what starts the notebook's kernel session; tell the person it is in the
   Browser tab. Without the browser, give the person that address to open.
4. **Pair with marimo-pair.** Load the `marimo-pair` skill and run its scripts from its
   skill directory with `--url http://127.0.0.1:PORT` and the token in the environment,
   `MARIMO_TOKEN="$(cat TOKEN_FILE)"`: first the `help(cm)` inspection it requires, then
   your code. Its server discovery lists only servers without a token, so pass `--url`. Scratchpad code reads the live notebook; changes that should
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
7. **Stop the server** (cancel its background task) and delete `TOKEN_FILE` when the
   person is done with it or asks; until then it keeps running between turns.
