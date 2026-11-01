"""Connected data sources, NDP and knowledge stores."""

from clio_agent.sdk import native_tool

# The NDP endpoint and publishing tools follow a search; they are deferred (named in the
# prompt, loaded with search_tools) so sessions that never reach NDP do not carry them.

connected_data_status = native_tool("connected_data_status")
connected_data_connect = native_tool("connected_data_connect")
connected_data_index = native_tool("connected_data_index")
connected_data_open = native_tool("connected_data_open")
connected_data_download = native_tool("connected_data_download")
connected_data_write = native_tool("connected_data_write")
connected_data_search_ndp = native_tool("connected_data_search_ndp")
connected_data_ndp_organizations = native_tool("connected_data_ndp_organizations", defer=True)
connected_data_ndp_endpoint_connect = native_tool("connected_data_ndp_endpoint_connect", defer=True)
connected_data_ndp_endpoint_operations = native_tool(
    "connected_data_ndp_endpoint_operations", defer=True
)
connected_data_ndp_upload_artifact = native_tool("connected_data_ndp_upload_artifact", defer=True)
connected_data_ndp_endpoint_request = native_tool("connected_data_ndp_endpoint_request", defer=True)
knowledge_open = native_tool("knowledge_open")
knowledge_search = native_tool("knowledge_search")
knowledge_related = native_tool("knowledge_related")
knowledge_create = native_tool("knowledge_create")
knowledge_edit = native_tool("knowledge_edit")
