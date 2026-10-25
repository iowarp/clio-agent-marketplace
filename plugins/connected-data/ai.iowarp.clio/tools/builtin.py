"""Connected data sources, NDP and knowledge stores."""

from clio_agent.sdk import native_tool

connected_data_status = native_tool("connected_data_status")
connected_data_connect = native_tool("connected_data_connect")
connected_data_index = native_tool("connected_data_index")
connected_data_open = native_tool("connected_data_open")
connected_data_download = native_tool("connected_data_download")
connected_data_write = native_tool("connected_data_write")
connected_data_search_ndp = native_tool("connected_data_search_ndp")
connected_data_ndp_organizations = native_tool("connected_data_ndp_organizations")
connected_data_ndp_endpoint_connect = native_tool("connected_data_ndp_endpoint_connect")
connected_data_ndp_endpoint_operations = native_tool("connected_data_ndp_endpoint_operations")
connected_data_ndp_upload_artifact = native_tool("connected_data_ndp_upload_artifact")
connected_data_ndp_endpoint_request = native_tool("connected_data_ndp_endpoint_request")
knowledge_open = native_tool("knowledge_open")
knowledge_search = native_tool("knowledge_search")
knowledge_related = native_tool("knowledge_related")
knowledge_create = native_tool("knowledge_create")
knowledge_edit = native_tool("knowledge_edit")
