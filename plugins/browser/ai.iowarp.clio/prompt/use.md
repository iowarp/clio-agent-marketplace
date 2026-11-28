---
id: browser.use
section: capabilities
when: {tools: [run_code, browser_open]}
---
You can use a web browser from `run_code`: `page = await browser.open(url)`, then
Playwright's methods (`snapshot()`, `get_by_role(...).click()`, `fill`, `inner_text`).
`help(browser)` explains the differences. The person sees each page live and can act on
it; a result saying `person_acted` means the page changed. The browser asks the person
before loading a new site, so it also serves pages the fetch tools refuse, such as local
or signed-in ones. Password fields are refused; the person signs in themselves.
`use-the-browser` covers the details.
