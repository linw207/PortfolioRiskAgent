from __future__ import annotations

from typing import Any

from src.domain.tool import MCPToolResult, MCPToolSpec
from src.infra.adapter.mcp.registry import MCPToolRegistry
from src.infra.external.search_gateway import AdvancedSearchGateway


def register_search_tools(registry: MCPToolRegistry, search_gateway: AdvancedSearchGateway) -> None:
    def web_search(arguments: dict[str, Any]) -> MCPToolResult:
        data = search_gateway.search(
            query=arguments["query"],
            max_results=arguments.get("max_results"),
            domains=arguments.get("domains"),
            search_type=arguments.get("search_type", "general"),
        )
        return MCPToolResult(
            success=data["success"],
            data=data,
            source=data.get("backend", "none"),
            error_code=None if data["success"] else "SEARCH_BACKEND_UNAVAILABLE",
            error_message="" if data["success"] else data.get("message", ""),
            degraded=not data["success"],
        )

    def trusted_news_search(arguments: dict[str, Any]) -> MCPToolResult:
        data = search_gateway.trusted_news_search(
            query=arguments["query"],
            max_results=arguments.get("max_results"),
        )
        return MCPToolResult(
            success=data["success"],
            data=data,
            source=data.get("backend", "none"),
            error_code=None if data["success"] else "SEARCH_BACKEND_UNAVAILABLE",
            error_message="" if data["success"] else data.get("message", ""),
            degraded=not data["success"],
        )

    def trusted_announcement_search(arguments: dict[str, Any]) -> MCPToolResult:
        data = search_gateway.trusted_announcement_search(
            symbol=arguments["symbol"],
            company_name=arguments.get("company_name", ""),
            keywords=arguments.get("keywords"),
        )
        return MCPToolResult(
            success=data["success"],
            data=data,
            source=data.get("backend", "none"),
            error_code=None if data["success"] else "SEARCH_BACKEND_UNAVAILABLE",
            error_message="" if data["success"] else data.get("message", ""),
            degraded=not data["success"],
        )

    specs = [
        MCPToolSpec(
            name="web_search",
            description="统一联网搜索工具。hybrid 模式下优先 Tavily，失败后降级 SerpAPI；无 key 时明确提示配置。",
            input_schema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"},
                    "domains": {"type": "array"},
                    "search_type": {"type": "string"},
                },
            },
            output_schema={"type": "object"},
            error_codes={"SEARCH_BACKEND_UNAVAILABLE": "无可用搜索后端或搜索失败"},
            data_source="Tavily/SerpAPI",
            handler=web_search,
            mature_tool_hint="Tavily Search API; SerpAPI Google Search API",
        ),
        MCPToolSpec(
            name="trusted_news_search",
            description="可信新闻搜索。用于上市公司风险、舆情和财报相关新闻，统一输出标题、摘要、链接和来源。",
            input_schema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"},
                },
            },
            output_schema={"type": "object"},
            error_codes={"SEARCH_BACKEND_UNAVAILABLE": "无可用搜索后端或搜索失败"},
            data_source="Tavily/SerpAPI",
            handler=trusted_news_search,
            mature_tool_hint="Tavily for AI-search summary; SerpAPI for Google organic results",
        ),
        MCPToolSpec(
            name="trusted_announcement_search",
            description="可信公告搜索。优先限制到巨潮资讯、上交所、深交所、证监会等域名。",
            input_schema={
                "type": "object",
                "required": ["symbol"],
                "properties": {
                    "symbol": {"type": "string"},
                    "company_name": {"type": "string"},
                    "keywords": {"type": "array"},
                },
            },
            output_schema={"type": "object"},
            error_codes={"SEARCH_BACKEND_UNAVAILABLE": "无可用搜索后端或搜索失败"},
            data_source="Tavily/SerpAPI trusted domains",
            handler=trusted_announcement_search,
            mature_tool_hint="Tavily include_domains; SerpAPI site: domain filters",
        ),
    ]
    for spec in specs:
        if registry.get(spec.name) is None:
            registry.register(spec)
