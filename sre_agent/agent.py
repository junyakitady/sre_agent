import google.auth
from google.auth.transport.requests import Request
from google.genai import types
from google.adk.agents import Agent
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.models import Gemini
from google.adk.plugins.reflect_retry_tool_plugin import ReflectAndRetryToolPlugin
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

_cached_creds = None
_cached_project_id = None
_auth_request = Request()


def gcp_auth_headers(context=None) -> dict[str, str]:
    global _cached_creds, _cached_project_id
    if _cached_creds is None:
        _cached_creds, _cached_project_id = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

    if not _cached_creds.valid:
        _cached_creds.refresh(_auth_request)

    if not _cached_creds.token:
        raise ValueError("GCPアクセストークンの取得に失敗しました。")

    headers = {"Authorization": f"Bearer {_cached_creds.token}"}
    if _cached_project_id:
        headers["X-Goog-User-Project"] = _cached_project_id

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
    model=Gemini(
        model='gemini-4-argon',
        retry_options=types.HttpRetryOptions(initial_delay=1, attempts=3),
    ),
    name='sre_agent',
    description='Google Cloud Logging の調査と技術知識の提供をサポートするSREエージェント',
    instruction="""You are an expert Google Cloud Site Reliability Engineer (SRE).
Your task is to help users manage, audit, and troubleshoot their Google Cloud resources.

You have access to two MCP servers:
1. Google Cloud Logging MCP server: Allows you to inspect logs and perform queries.
2. Google Developer Knowledge MCP server: Provides official documentation and grounded answers about Google developer products, APIs, SDKs, and cloud architecture.

When answering user queries:
- Always check Cloud Logging first if the request is about diagnosing issues or finding resource names. If the user has not specified a target project ID, ask them to provide it before querying logs.
- For technical questions regarding Google Cloud services, APIs, SDKs, or best practices, prioritize using the Google Developer Knowledge MCP server (preferring search_documents and get_documents) to retrieve official, up-to-date information, and cite the source URLs.
- Be precise and concise in your SRE diagnosis, and respond in the same language as the user's query.
- Avoid exposing technical credentials or internal implementation details.
""",
    tools=[cloud_logging_tools, dev_knowledge_tools]
)

app = App(
    name='sre_agent',
    root_agent=root_agent,
    plugins=[ReflectAndRetryToolPlugin()],
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=10,
        overlap_size=2,
        token_threshold=700000,
        event_retention_size=2
    )
)

