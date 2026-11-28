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

## Reading a page

- A page comes from `page = await browser.open(url)` or `await browser.page(id)`.
- `print(await page.snapshot())` shows its structure. Each element has a ref
  (`[ref=f9e14]`); `page.get_by_ref("f9e14")` addresses it until the page changes.
- Locators by role and name (`page.get_by_role("button", name="Save")`), label
  (`get_by_label`) or text hold up better than CSS. A locator that matches several
  elements fails with the count; `filter(has_text=...)`, `nth(i)`, `first` or `last`
  narrow it.
- One script can do the whole job: loop over pages of a listing, collect rows into
  Python values, and print only what the answer needs.
- `browser.pages()` shows pages this conversation already has open for a site, and
  `await page.close()` frees one: the server keeps a limited number of pages open for
  every conversation together.

## Sites and sign-ins

- Loading a site this conversation has not used asks the person once. If they refuse,
  the call raises `ToolError` with `browser_host_denied`, and the work continues without
  that site.
- When a result's page has `navigation_blocked`, the page was refused: a scheme the
  browser does not open (its `reason` is `browser_scheme_refused`) or a failure of the
  host check (`browser_host_gate_error`, with `detail`). The person cannot see what was
  refused and why unless told; a site they did not allow raises `browser_host_denied`
  instead.
- Password fields are the person's: typing into one is refused with
  `browser_password_field`. The person signs in in the Browser tab and says when they
  are done; the page then shows the signed-in state. The sign-in is kept for later
  conversations.
- A device on a home or lab network often has a certificate the browser does not trust:
  the call raises `browser_certificate_untrusted` and the page stays on the browser's
  warning. Only the person can trust it, from the Browser tab, using the host and
  fingerprint the error names; getting around the warning is not the agent's decision.
- `browser_host_unreachable` means the host did not answer the computer the agent runs on.
  The error says where that is; the address itself is usually not the problem, and a
  retry gets the same answer.

## Sharing the page

- When a result says `person_acted`, the person used the page since your last call, so
  what you saw before may have changed.
- `await page.screenshot()` returns a PNG path in the scratch folder; `view_image` shows
  it when the layout matters. The script prints the screenshot's `artifact://` link,
  which shows the image in an answer.
- Downloads land in the session's scratch folder; the call that triggered one lists it
  in `page.downloads`.
- `page.evaluate(...)` runs JavaScript with the person's sign-ins, so it asks first; a
  locator or read usually gets the value without it.
