"""Connected data sources and knowledge stores.

The National Data Platform's own tools belong to the ndp plugin.
"""

from clio_agent.sdk import native_tool

# Attaching and reading a source is listed (defer=False): it is how data from a
# catalog reaches the workspace instead of the context. Indexing, writing and the
# knowledge-store tools are deferred until a session needs them.
connected_data_status = native_tool("connected_data_status", defer=False)
connected_data_connect = native_tool("connected_data_connect", defer=False)
connected_data_open = native_tool("connected_data_open", defer=False)
connected_data_download = native_tool("connected_data_download", defer=False)
connected_data_index = native_tool("connected_data_index", defer=True)
connected_data_write = native_tool("connected_data_write", defer=True)
knowledge_open = native_tool("knowledge_open", defer=True)
knowledge_search = native_tool("knowledge_search", defer=True)
knowledge_related = native_tool("knowledge_related", defer=True)
knowledge_create = native_tool("knowledge_create", defer=True)
knowledge_edit = native_tool("knowledge_edit", defer=True)
