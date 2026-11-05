---
name: use-the-browser
title: Use the browser
description: Use to read, search or operate a website from a run_code script with the shared browser - paging through listings, filling forms, downloading files, or continuing on a page the person signed in to.
keywords:
- browser
- web
- website
- page
- form
- sign in
---

# Use the browser

The browser is reached from a `run_code` script through `browser`, with Playwright's
names. Every page is shared with the person, who sees it live in the Browser tab and can
click and type in it too. Pages belong to this conversation and stay open between
scripts: `await browser.pages()` lists them and `await browser.page("p2")` returns one,
so a page survives a stopped script or a restarted kernel.

## Look before you act

1. Open or reach the page: `page = await browser.open(url)` or `await browser.page(id)`.
2. Read its structure with `print(await page.snapshot())`. Each element has a ref
   (`[ref=f9e14]`); `page.get_by_ref("f9e14")` addresses it until the page changes.
3. Prefer locators by role and name (`page.get_by_role("button", name="Save")`), label
   (`get_by_label`) or text over CSS. A locator that matches several elements fails with
   the count: narrow it with `filter(has_text=...)`, `nth(i)`, `first` or `last`.
4. Do the work in one script: loop over pages of a listing, collect rows into Python
   values, and print only what the answer needs.
5. Reuse a page this conversation already has open for the site (`browser.pages()`)
   instead of opening another, and `await page.close()` pages you no longer need: the
   server keeps a limited number of pages open for every conversation together.

## Sites and sign-ins

- Loading a site this conversation has not used asks the person once. If they refuse,
  the call raises `ToolError` with `browser_host_denied`; say so and go on without it.
- When a result's page has `navigation_blocked`, the page was refused: a scheme the
  browser does not open (its `reason` is `browser_scheme_refused`) or a failure of the
  host check (`browser_host_gate_error`, with `detail`). Tell the person what was
  refused and why; a site they did not allow raises `browser_host_denied` instead.
- Never type into a password field (it is refused with `browser_password_field`). Ask
  the person to sign in in the Browser tab, wait for them to say they are done, then read
  the page again. The sign-in is kept for later conversations.
- A device on a home or lab network often has a certificate the browser does not trust:
  the call raises `browser_certificate_untrusted` and the page stays on the browser's
  warning. Only the person can trust it, from the Browser tab. Ask them, with the host and
  fingerprint the error names, and wait; never try to get around the warning.
- `browser_host_unreachable` means the host did not answer the computer the agent runs on.
  Tell the person what the error says about where that is; do not blame the address or
  retry it.

## Sharing the page

- When a result says `person_acted`, the person used the page since your last call:
  read it again before you act on what you saw.
- `await page.screenshot()` returns a PNG path in the scratch folder; look at it with
  `view_image` when the layout matters. The script prints the screenshot's
  `artifact://` link, which shows the image in an answer.
- Downloads land in the session's scratch folder; the call that triggered one lists it
  in `page.downloads`.
- `page.evaluate(...)` runs JavaScript with the person's sign-ins, so it asks first; use
  it only when no locator or read can get the value.
