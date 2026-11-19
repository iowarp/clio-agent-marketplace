"""A2UI surface producers, capture and dashboard publishing."""

from clio_agent.sdk import native_tool

# Building a surface is listed; inspecting, capturing, deleting and publishing one are
# deferred: named in the prompt and loaded with search_tools when a surface exists.

# defer=False is needed: a tool that declares nothing is deferred with every other
# built-in (tools.defer_builtins), and then neither it nor the guidance gated on it
# reaches the agent, which falls back to static images.
create_a2ui_surface = native_tool("create_a2ui_surface", defer=False)
update_a2ui_components = native_tool("update_a2ui_components", defer=False)
update_a2ui_data_model = native_tool("update_a2ui_data_model", defer=False)
delete_a2ui_surface = native_tool("delete_a2ui_surface", defer=True)
inspect_a2ui_surface = native_tool("inspect_a2ui_surface", defer=True)
capture_a2ui_surface = native_tool("capture_a2ui_surface", defer=True)
publish_dashboard_report = native_tool("publish_dashboard_report", defer=True)
