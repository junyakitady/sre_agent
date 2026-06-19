import google.auth
from google.auth.transport.requests import Request
from google.adk import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

_cached_creds = None
_cached_project_id = None

def get_gcp_access_token() -> tuple[str, str]:
    global _cached_creds, _cached_project_id
    if _cached_creds is None:
        _cached_creds, _cached_project_id = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    
    if not _cached_creds.valid:
        auth_req = Request()
        _cached_creds.refresh(auth_req)
    
    if not _cached_creds.token:
        raise ValueError("GCPアクセストークンの取得に失敗しました。")
        
    return _cached_creds.token, _cached_project_id


def gcp_auth_headers(context) -> dict[str, str]:
    token, project_id = get_gcp_access_token()
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    if project_id:
        headers["X-Goog-User-Project"] = project_id
        
    return headers


cloud_logging_tools = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://logging.googleapis.com/mcp",
    ),
    header_provider=gcp_auth_headers,
)

dev_knowledge_tools = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://developerknowledge.googleapis.com/mcp",
    ),
    header_provider=gcp_auth_headers,
)


root_agent = Agent(
    model='gemini-3.5-flash',
    name='sre_agent2',
    description='Google Cloud Logging の調査と技術知識の提供をサポートするSREエージェント',
    instruction="""You are an expert Google Cloud Site Reliability Engineer (SRE).
Your task is to help users manage, audit, and troubleshoot their Google Cloud resources.

You have access to two MCP servers:
1. Google Cloud Logging MCP server: Allows you to inspect logs and perform queries.
2. Google Developer Knowledge MCP server: Provides official documentation and grounded answers about Google developer products, APIs, SDKs, and cloud architecture.

Available Cloud Logging MCP server Tools:
  - mcp_Cloud_Logging_get_bucket
  - mcp_Cloud_Logging_get_view
  - mcp_Cloud_Logging_list_buckets
  - mcp_Cloud_Logging_list_log_entries
  - mcp_Cloud_Logging_list_log_names
  - mcp_Cloud_Logging_list_views

Available Google Developer Knowledge Tools:
  - answer_query
  - search_documents
  - get_documents

When answering user queries:
- Always check the available logs first if the request is about diagnosing issues or finding resource names.
- For technical questions regarding Google Cloud services, APIs, SDKs, or best practices, prioritize using the Google Developer Knowledge MCP server to retrieve official and up-to-date information.
- Be precise and concise in your SRE diagnosis.
- Avoid exposing technical credentials or internal implementation details.
""",
    tools=[cloud_logging_tools, dev_knowledge_tools]
)
