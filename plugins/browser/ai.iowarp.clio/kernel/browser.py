"""``browser``: drive this conversation's web pages from a script, with Playwright's names.

    page = await browser.open("https://arxiv.org/list/cs.DC/new")
    print(await page.snapshot())                    # the page's structure, with refs
    entries = page.get_by_role("listitem").filter(has_text="HDF5")
    for i in range(await entries.count()):
        print(await entries.nth(i).inner_text())
    await page.get_by_label("Search term").fill("parallel I/O")
    await page.keyboard.press("Enter")
    await page.wait_for_load_state()
    shot = await page.screenshot(full_page=True)    # a path; look at it with view_image

``browser.open(url)`` opens a page for this conversation, ``browser.pages()`` lists them and
``browser.page("p2")`` returns one by id, so a page opened in an earlier script, or by the
person in the shared tab, is reachable after the kernel restarts. The person sees every page
live and can act on it too: when a result says ``page.person_acted``, read the page again
before acting on it. A site this conversation has not loaded before is a question to the
person; the call waits for the answer, and a refusal raises ``ToolError``.

Where it differs from Playwright:

- every method is async;
- there are no element handles, ``page.on(...)`` events, ``expect_*`` waiters or routes;
  use the ``wait_for_*`` methods, and ``set_input_files`` on a file input to upload;
- ``screenshot`` returns a file path rather than bytes;
- ``evaluate`` takes and returns JSON values only;
- the agent never types into a password field: ask the person to sign in in the shared
  tab, then continue on the signed-in page;
- errors are ``ToolError`` carrying the tool's typed reason (``browser_host_denied``,
  ``browser_target_ambiguous: ... resolved to 3 elements``, ``browser_password_field``).

Locators are data: ``get_by_*``, ``locator``, ``frame_locator``, ``filter``, ``nth``,
``first`` and ``last`` only describe an element, and nothing reaches the page until a
method like ``click``, ``fill`` or ``inner_text`` runs. An action on a locator that matches
several elements fails with the count, so narrow it.
"""

from __future__ import annotations

from typing import Any


async def _call(name: str, **args: Any) -> Any:
    return await tools.call(name, **args)  # noqa: F821 - bound by the kernel


def _notice(text: str) -> None:
    import sys

    print(f"[browser] {text}", file=sys.stderr)


def _ms(timeout: float | None) -> float | None:
    return None if timeout is None else float(timeout) / 1000


class Locator:
    """An element description; its methods act on or read the element it matches."""

    def __init__(self, page: "Page", steps: list[dict[str, Any]], frame: list[Any]) -> None:
        self._page = page
        self._steps = steps
        self._frame = frame

    def __repr__(self) -> str:
        return f"<Locator {self._steps!r} on {self._page.id}>"

    def _target(self) -> dict[str, Any]:
        return {"steps": self._steps, **({"frame": self._frame} if self._frame else {})}

    def _with(self, step: dict[str, Any]) -> "Locator":
        return Locator(self._page, [*self._steps, step], self._frame)

    # ---- narrowing (no tool call) --------------------------------------------------
    def get_by_role(
        self, role: str, *, name: str | None = None, exact: bool = False, **options: Any
    ) -> "Locator":
        step = {"by": "role", "role": role, "exact": exact, **options}
        if name is not None:
            step["name"] = name
        return self._with(step)

    def get_by_text(self, text: str, *, exact: bool = False) -> "Locator":
        return self._with({"by": "text", "text": text, "exact": exact})

    def get_by_label(self, text: str, *, exact: bool = False) -> "Locator":
        return self._with({"by": "label", "text": text, "exact": exact})

    def get_by_placeholder(self, text: str, *, exact: bool = False) -> "Locator":
        return self._with({"by": "placeholder", "text": text, "exact": exact})

    def get_by_alt_text(self, text: str, *, exact: bool = False) -> "Locator":
        return self._with({"by": "alt", "text": text, "exact": exact})

    def get_by_title(self, text: str, *, exact: bool = False) -> "Locator":
        return self._with({"by": "title", "text": text, "exact": exact})

    def get_by_test_id(self, test_id: str) -> "Locator":
        return self._with({"by": "test_id", "test_id": test_id})

    def locator(self, selector: str) -> "Locator":
        return self._with({"by": "css", "css": selector})

    def filter(
        self,
        *,
        has_text: str | None = None,
        has_not_text: str | None = None,
        visible: bool | None = None,
    ) -> "Locator":
        step: dict[str, Any] = {"by": "filter"}
        for key, value in (
            ("has_text", has_text),
            ("has_not_text", has_not_text),
            ("visible", visible),
        ):
            if value is not None:
                step[key] = value
        return self._with(step)

    def nth(self, index: int) -> "Locator":
        return self._with({"by": "nth", "index": int(index)})

    @property
    def first(self) -> "Locator":
        return self._with({"by": "first"})

    @property
    def last(self) -> "Locator":
        return self._with({"by": "last"})

    # ---- actions -------------------------------------------------------------------
    async def _act(self, action: str, value: Any = None, **options: Any) -> None:
        await self._page._run(
            "browser_act",
            action=action,
            target=self._target(),
            value=value,
            options=options or None,
        )

    async def click(self, **options: Any) -> None:
        await self._act("click", **options)

    async def dblclick(self, **options: Any) -> None:
        await self._act("dblclick", **options)

    async def hover(self, **options: Any) -> None:
        await self._act("hover", **options)

    async def fill(self, value: str) -> None:
        await self._act("fill", value)

    async def press_sequentially(self, text: str, **options: Any) -> None:
        await self._act("type", text, **options)

    type = press_sequentially

    async def press(self, key: str) -> None:
        await self._act("press", key)

    async def select_option(self, value: Any) -> None:
        await self._act("select", value)

    async def check(self, **options: Any) -> None:
        await self._act("check", **options)

    async def uncheck(self, **options: Any) -> None:
        await self._act("uncheck", **options)

    async def set_input_files(self, files: str | list[str]) -> None:
        await self._act("upload", files)

    async def drag_to(self, target: "Locator") -> None:
        await self._act("drag_to", target._target())

    async def scroll_into_view_if_needed(self) -> None:
        await self._act("scroll")

    # ---- reads ---------------------------------------------------------------------
    async def _read(self, what: str, name: str | None = None) -> Any:
        result = await self._page._run("browser_read", target=self._target(), what=what, name=name)
        return result.get("value")

    async def inner_text(self) -> str:
        return await self._read("text")

    async def inner_html(self) -> str:
        return await self._read("inner_html")

    async def input_value(self) -> str:
        return await self._read("value")

    async def get_attribute(self, name: str) -> str | None:
        return await self._read("attribute", name)

    async def count(self) -> int:
        return await self._read("count")

    async def bounding_box(self) -> dict[str, float] | None:
        return await self._read("box")

    async def is_visible(self) -> bool:
        return await self._read("visible")

    async def is_checked(self) -> bool:
        return await self._read("checked")

    async def all_inner_texts(self) -> list[str]:
        """Each matching element's text (one read per element)."""
        return [await self.nth(i).inner_text() for i in range(await self.count())]

    async def wait_for(self, *, state: str = "visible", timeout: float | None = None) -> None:
        until = "gone" if state in ("hidden", "detached") else "target"
        await self._page._run(
            "browser_wait", until=until, target=self._target(), timeout_s=_ms(timeout)
        )

    async def screenshot(self) -> str:
        result = await self._page._run("browser_screenshot", target=self._target())
        return result["screenshot"]["path"]

    async def aria_snapshot(self, *, boxes: bool = False) -> str:
        result = await self._page._run("browser_snapshot", target=self._target(), boxes=boxes)
        return result["snapshot"]


class FrameLocator:
    """The content of an iframe; ``get_by_*`` and ``locator`` address elements inside it."""

    def __init__(self, page: "Page", frame: list[Any]) -> None:
        self._page = page
        self._frame = frame

    def _root(self, step: dict[str, Any]) -> Locator:
        return Locator(self._page, [step], self._frame)

    def locator(self, selector: str) -> Locator:
        return self._root({"by": "css", "css": selector})

    def get_by_role(
        self, role: str, *, name: str | None = None, exact: bool = False, **options: Any
    ) -> Locator:
        step = {"by": "role", "role": role, "exact": exact, **options}
        if name is not None:
            step["name"] = name
        return self._root(step)

    def get_by_text(self, text: str, *, exact: bool = False) -> Locator:
        return self._root({"by": "text", "text": text, "exact": exact})

    def get_by_label(self, text: str, *, exact: bool = False) -> Locator:
        return self._root({"by": "label", "text": text, "exact": exact})

    def frame_locator(self, selector: str) -> "FrameLocator":
        return FrameLocator(self._page, [*self._frame, {"by": "css", "css": selector}])


class Keyboard:
    """Keys for the focused element."""

    def __init__(self, page: "Page") -> None:
        self._page = page

    async def press(self, key: str) -> None:
        await self._page._run("browser_act", action="key", value=key)

    async def type(self, text: str) -> None:
        await self._page._run("browser_act", action="type", value=text)


class Mouse:
    """The pointer, in page CSS pixels."""

    def __init__(self, page: "Page") -> None:
        self._page = page

    async def click(self, x: float, y: float, **options: Any) -> None:
        await self._page._run(
            "browser_act", action="mouse_click", x=x, y=y, options=options or None
        )

    async def wheel(self, delta_x: float, delta_y: float) -> None:
        await self._page._run("browser_act", action="scroll", x=delta_x, y=delta_y)


class Page:
    """One page of this conversation, shared with the person."""

    def __init__(self, info: dict[str, Any]) -> None:
        self.id = str(info.get("id") or "")
        self.url = str(info.get("url") or "")
        self._title = str(info.get("title") or "")
        self.host = str(info.get("host") or "")
        #: From the last call: the person used this page since the agent's previous call.
        self.person_acted = False
        #: From the last call: a host the page tried to load and was refused, if any.
        self.navigation_blocked: dict[str, Any] | None = None
        #: From the last call: files it downloaded (in the session's scratch folder).
        self.downloads: list[dict[str, Any]] = []
        self.keyboard = Keyboard(self)
        self.mouse = Mouse(self)

    def __repr__(self) -> str:
        return f"<Page {self.id} {self.url}>"

    async def _run(self, tool: str, **args: Any) -> dict[str, Any]:
        result = await _call(tool, page=self.id, **{k: v for k, v in args.items() if v is not None})
        self._update(result)
        return result

    def _update(self, result: Any) -> None:
        if not isinstance(result, dict):
            return
        info = result.get("page") or {}
        self.url = str(info.get("url") or self.url)
        self._title = str(info.get("title") or self._title)
        self.host = str(info.get("host") or self.host)
        self.person_acted = bool(result.get("person_acted"))
        self.navigation_blocked = result.get("navigation_blocked")
        self.downloads = list(result.get("downloads") or [])
        # The model reads what the script prints, so what changed under the script is said.
        if self.person_acted:
            _notice(f"the person used page {self.id} since your last call on it; read it again")
        if self.navigation_blocked:
            blocked = self.navigation_blocked
            _notice(
                f"page {self.id} tried to open {blocked.get('host')}, which is not allowed "
                f"here ({blocked.get('reason')}); the page stayed where it was"
            )

    # ---- locators (no tool call) ---------------------------------------------------
    def _root(self, step: dict[str, Any]) -> Locator:
        return Locator(self, [step], [])

    def get_by_role(
        self, role: str, *, name: str | None = None, exact: bool = False, **options: Any
    ) -> Locator:
        step = {"by": "role", "role": role, "exact": exact, **options}
        if name is not None:
            step["name"] = name
        return self._root(step)

    def get_by_text(self, text: str, *, exact: bool = False) -> Locator:
        return self._root({"by": "text", "text": text, "exact": exact})

    def get_by_label(self, text: str, *, exact: bool = False) -> Locator:
        return self._root({"by": "label", "text": text, "exact": exact})

    def get_by_placeholder(self, text: str, *, exact: bool = False) -> Locator:
        return self._root({"by": "placeholder", "text": text, "exact": exact})

    def get_by_alt_text(self, text: str, *, exact: bool = False) -> Locator:
        return self._root({"by": "alt", "text": text, "exact": exact})

    def get_by_title(self, text: str, *, exact: bool = False) -> Locator:
        return self._root({"by": "title", "text": text, "exact": exact})

    def get_by_test_id(self, test_id: str) -> Locator:
        return self._root({"by": "test_id", "test_id": test_id})

    def get_by_ref(self, ref: str) -> Locator:
        """The element a snapshot named ``[ref=f9e14]`` (the latest snapshot of this page)."""
        return self._root({"by": "ref", "ref": ref})

    def locator(self, selector: str) -> Locator:
        return self._root({"by": "css", "css": selector})

    def frame_locator(self, selector: str) -> FrameLocator:
        return FrameLocator(self, [{"by": "css", "css": selector}])

    # ---- the page ------------------------------------------------------------------
    async def title(self) -> str:
        """The page's title, as of the latest call on it."""
        return self._title

    async def content(self) -> str:
        """The page's HTML."""
        return await self.evaluate("() => document.documentElement.outerHTML")

    async def inner_text(self, selector: str) -> str:
        return await self.locator(selector).inner_text()

    async def text_content(self, selector: str) -> str:
        return await self.locator(selector).inner_text()

    async def click(self, selector: str, **options: Any) -> None:
        await self.locator(selector).click(**options)

    async def fill(self, selector: str, value: str) -> None:
        await self.locator(selector).fill(value)

    async def goto(self, url: str, *, wait_until: str = "load") -> int | None:
        result = await self._run("browser_navigate", url=url, action="goto", wait_until=wait_until)
        return result.get("status")

    async def go_back(self, *, wait_until: str = "load") -> None:
        await self._run("browser_navigate", action="back", wait_until=wait_until)

    async def go_forward(self, *, wait_until: str = "load") -> None:
        await self._run("browser_navigate", action="forward", wait_until=wait_until)

    async def reload(self, *, wait_until: str = "load") -> None:
        await self._run("browser_navigate", action="reload", wait_until=wait_until)

    async def snapshot(self, *, boxes: bool = False) -> str:
        """The page's accessibility tree as text, each element with a ref for get_by_ref."""
        result = await self._run("browser_snapshot", boxes=boxes)
        return result["snapshot"]

    aria_snapshot = snapshot

    async def screenshot(self, *, full_page: bool = False) -> str:
        """Write a PNG to the session's scratch folder and return its path."""
        result = await self._run("browser_screenshot", full_page=full_page)
        return result["screenshot"]["path"]

    async def evaluate(self, expression: str, arg: Any = None) -> Any:
        result = await self._run("browser_evaluate", expression=expression, arg=arg)
        return result.get("value")

    async def wait_for_url(self, url: str, *, timeout: float | None = None) -> None:
        await self._run("browser_wait", until="url", value=url, timeout_s=_ms(timeout))

    async def wait_for_load_state(
        self, state: str = "load", *, timeout: float | None = None
    ) -> None:
        until = "idle" if state == "networkidle" else "load"
        value = None if until == "idle" else state
        await self._run("browser_wait", until=until, value=value, timeout_s=_ms(timeout))

    async def wait_for_selector(
        self, selector: str, *, state: str = "visible", timeout: float | None = None
    ) -> None:
        await self.locator(selector).wait_for(state=state, timeout=timeout)

    async def wait_for_timeout(self, timeout: float) -> None:
        """Sleep ``timeout`` milliseconds (no call reaches the page)."""
        import asyncio

        await asyncio.sleep(float(timeout) / 1000)

    async def close(self) -> None:
        await _call("browser_close", page=self.id)


class Browser:
    """This conversation's pages."""

    def __repr__(self) -> str:
        return "<browser: open(url), pages(), page(id); help(browser) explains>"

    async def open(self, url: str | None = None, *, label: str = "") -> Page:
        """Open a page, loading ``url`` when given."""
        result = await _call("browser_open", **({"url": url} if url else {}), label=label)
        page = Page(result["page"])
        page._update(result)
        return page

    async def pages(self) -> list[Page]:
        """Every page this conversation has open, including ones the person opened."""
        result = await _call("browser_pages")
        return [Page(info) for info in result.get("pages") or []]

    async def page(self, page_id: str) -> Page:
        """One open page by id, such as ``p2``."""
        for page in await self.pages():
            if page.id == page_id:
                return page
        raise ToolError(f"browser_page_not_found: this conversation has no page {page_id!r}")  # noqa: F821


Browser.__doc__ = __doc__  # help(browser) explains the whole binding
export = Browser()
