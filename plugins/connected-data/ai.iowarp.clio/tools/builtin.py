"""Connected data sources and knowledge stores.

The National Data Platform's own tools belong to the ndp plugin.
"""

from clio_agent.sdk import native_tool

connected_data_status = native_tool("connected_data_status")
connected_data_connect = native_tool("connected_data_connect")
connected_data_index = native_tool("connected_data_index")
connected_data_open = native_tool("connected_data_open")
connected_data_download = native_tool("connected_data_download")
connected_data_write = native_tool("connected_data_write")
knowledge_open = native_tool("knowledge_open")
knowledge_search = native_tool("knowledge_search")
knowledge_related = native_tool("knowledge_related")
knowledge_create = native_tool("knowledge_create")
knowledge_edit = native_tool("knowledge_edit")
