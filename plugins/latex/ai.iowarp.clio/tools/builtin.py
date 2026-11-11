"""LaTeX builds, implemented by CLIO: build a paper, read its outline, map PDF and source."""

from clio_agent.sdk import native_tool

latex_build = native_tool("latex_build")
latex_outline = native_tool("latex_outline")
latex_locate = native_tool("latex_locate")
