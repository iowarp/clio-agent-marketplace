"""The National Data Platform tools built into CLIO, claimed by the ndp plugin.

Discovery is credential-free and needs no MCP server. Endpoint operations follow a
search or a saved Endpoint; they are deferred (named in the prompt, loaded with
search_tools) so a session that never reaches an Endpoint does not carry them.
"""

from clio_agent.sdk import native_tool

# Discovery is listed (defer=False). A tool that declares nothing is deferred with
# every other built-in (tools.defer_builtins); these were, and an agent given the ndp
# connector used its MCP tools instead, reading the catalog anonymously into context.
connected_data_search_ndp = native_tool("connected_data_search_ndp", defer=False)
connected_data_ndp_organizations = native_tool("connected_data_ndp_organizations", defer=False)
connected_data_ndp_tiles_covering = native_tool("connected_data_ndp_tiles_covering", defer=False)
connected_data_ndp_endpoint_connect = native_tool("connected_data_ndp_endpoint_connect", defer=True)
connected_data_ndp_endpoint_operations = native_tool(
    "connected_data_ndp_endpoint_operations", defer=True
)
connected_data_ndp_upload_artifact = native_tool("connected_data_ndp_upload_artifact", defer=True)
connected_data_ndp_endpoint_request = native_tool("connected_data_ndp_endpoint_request", defer=True)
