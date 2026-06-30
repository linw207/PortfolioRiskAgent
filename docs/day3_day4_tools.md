# Day3-4 MCP-Style Tools

## Design

The project uses an internal MCP-style tool boundary first, with a shape that can later be replaced by a standalone MCP server.

- `src/domain/tool.py`: `MCPToolSpec` and `MCPToolResult`.
- `src/infra/adapter/mcp/registry.py`: registration, whitelist check, schema validation, call dispatch, call audit.
- `src/infra/adapter/mcp/json_action.py`: JSON Action fallback parser with required fields `思考`、`动作`、`参数`.
- `src/infra/adapter/mcp/financial_toolkit.py`: Day4 financial tools.
- `src/app/service/tool_service.py`: application use case.
- `src/api/web/controller/tool_controller.py`: API boundary.

## Mature Tool Strategy

External mature tool preference:

1. AKShare for A-share market/index/announcement data.
2. Local curated sample data as deterministic fallback.
3. Same `MCPToolSpec` boundary can later wrap a standalone MCP server or Tushare adapter.

AKShare is optional at runtime. If it is not installed or returns empty data, the tool returns `degraded=true` and `source=local_sample` instead of inventing data.

## Registered Tools

- `get_stock_price`
- `get_index_price`
- `get_financial_metrics`
- `calculate_portfolio_risk`
- `search_announcements`
- `retrieve_evidence`
- `web_search`
- `trusted_news_search`
- `trusted_announcement_search`

## Advanced Search Strategy

The search tools follow the HelloAgents SearchTool design:

- Default backend is `hybrid`.
- Tavily is preferred when `TAVILY_API_KEY` exists.
- SerpAPI is used when Tavily is unavailable or fails.
- If both are missing, tools return a clear configuration message and do not fabricate online evidence.
- Local `.env` may contain real API keys, but keys must not be copied into docs, examples, commits, or logs.

Trusted source strategy:

- `web_search`: general web search with optional domain filters.
- `trusted_news_search`: company/news/risk search for market and media context.
- `trusted_announcement_search`: announcement and regulatory search restricted to mature trusted domains when supported:
  - `cninfo.com.cn`
  - `sse.com.cn`
  - `szse.cn`
  - `csrc.gov.cn`
- Announcement results are post-filtered: a result must match the stock code or company name. Risk keywords alone are not enough to become evidence.

Environment variables:

```bash
SEARCH_BACKEND=hybrid
TAVILY_API_KEY=...
SERPAPI_API_KEY=...
SEARCH_MAX_RESULTS=5
SEARCH_TIMEOUT_SECONDS=8
```

## API

```bash
GET /tools
POST /tools/{tool_name}/call
POST /tools/json-action
```

Example:

```json
{
  "arguments": {
    "symbol": "300750"
  },
  "task_id": "task_demo"
}
```
