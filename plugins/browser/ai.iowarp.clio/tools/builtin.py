"""The browser's tools, built into CLIO: reached from run_code scripts through the binding."""

from clio_agent.sdk import native_tool

browser_open = native_tool("browser_open", callers="code")
browser_pages = native_tool("browser_pages", callers="code")
browser_close = native_tool("browser_close", callers="code")
browser_navigate = native_tool("browser_navigate", callers="code")
browser_snapshot = native_tool("browser_snapshot", callers="code")
browser_read = native_tool("browser_read", callers="code")
browser_act = native_tool("browser_act", callers="code")
browser_wait = native_tool("browser_wait", callers="code")
browser_screenshot = native_tool("browser_screenshot", callers="code")
# A page script runs with the page's origin and the person's sign-ins, so it asks.
browser_evaluate = native_tool("browser_evaluate", callers="code", permission="ask")
