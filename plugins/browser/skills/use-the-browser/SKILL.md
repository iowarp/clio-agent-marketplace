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

## Sites and sign-ins

- Loading a site this conversation has not used asks the person once. If they refuse,
  the call raises `ToolError` with `browser_host_denied`; say so and go on without it.
- When a result's page has `navigation_blocked`, the page tried to go to a site that is
  not allowed; tell the person, who can allow it from the Browser tab.
- Never type into a password field (it is refused with `browser_password_field`). Ask
  the person to sign in in the Browser tab, wait for them to say they are done, then read
  the page again. The sign-in is kept for later conversations.

## Sharing the page

- When a result says `person_acted`, the person used the page since your last call:
  read it again before you act on what you saw.
- `await page.screenshot()` returns a PNG path; look at it with `view_image` when the
  layout matters.
- Downloads land in the session's scratch folder; the call that triggered one lists it
  in `page.downloads`.
- `page.evaluate(...)` runs JavaScript with the person's sign-ins, so it asks first; use
  it only when no locator or read can get the value.
