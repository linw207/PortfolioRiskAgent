from __future__ import annotations

from typing import Any

from src.app.service.risk_calculator import calculate_portfolio_risk
from src.app.service.validation import normalize_symbol
from src.domain.tool import MCPToolResult, MCPToolSpec
from src.infra.adapter.mcp.registry import MCPToolRegistry
from src.infra.external.market_data_gateway import MarketDataGateway


RISK_KEYWORDS = ["减持", "诉讼", "问询", "预亏", "质押", "退市", "监管"]


def register_financial_tools(registry: MCPToolRegistry, gateway: MarketDataGateway) -> None:
    def get_stock_price(arguments: dict[str, Any]) -> MCPToolResult:
        data, source, degraded = gateway.stock_quote(arguments["symbol"])
        data["source"] = source
        return MCPToolResult(success=True, data=data, source=source, degraded=degraded)

    def get_index_price(arguments: dict[str, Any]) -> MCPToolResult:
        data, source, degraded = gateway.index_quote(arguments.get("symbol", "000300.SH"))
        data["source"] = source
        return MCPToolResult(success=True, data=data, source=source, degraded=degraded)

    def get_financial_metrics(arguments: dict[str, Any]) -> MCPToolResult:
        data, source, degraded = gateway.financial_metrics(arguments["symbol"])
        return MCPToolResult(success=True, data=data, source=source, degraded=degraded)

    def calculate_risk(arguments: dict[str, Any]) -> MCPToolResult:
        holdings = []
        quotes = {}
        for item in arguments["holdings"]:
            symbol = normalize_symbol(item["symbol"])
            normalized = {**item, "symbol": symbol}
            holdings.append(normalized)
            quote, source, _degraded = gateway.stock_quote(symbol)
            quotes[symbol] = {**quote, "source": source}
        return MCPToolResult(
            success=True,
            data=calculate_portfolio_risk(holdings, quotes),
            source="risk_calculator",
        )

    def search_announcements(arguments: dict[str, Any]) -> MCPToolResult:
        data, source, degraded = gateway.announcements(
            arguments["symbol"],
            limit=arguments.get("limit", 10),
            keywords=arguments.get("keywords"),
        )
        return MCPToolResult(
            success=True,
            data={"symbol": normalize_symbol(arguments["symbol"]), "announcements": data},
            source=source,
            degraded=degraded,
        )

    def retrieve_evidence(arguments: dict[str, Any]) -> MCPToolResult:
        keywords = arguments.get("risk_keywords") or RISK_KEYWORDS
        announcements, source, degraded = gateway.announcements(
            arguments["symbol"],
            limit=arguments.get("limit", 5),
            keywords=keywords,
        )
        evidence = [
            {
                **item,
                "snippet": item.get("content", "")[:300],
                "matched_keywords": [
                    keyword for keyword in keywords if keyword in item.get("title", "") or keyword in item.get("content", "")
                ],
            }
            for item in announcements
        ]
        return MCPToolResult(
            success=True,
            data={"symbol": normalize_symbol(arguments["symbol"]), "evidence": evidence},
            source=source,
            degraded=degraded,
        )

    specs = [
        MCPToolSpec(
            name="get_stock_price",
            description="获取 A 股/港股个股行情。港股可优先 iTick 实时 tick，A 股优先 AKShare，失败时降级本地样例数据并标注 degraded。",
            input_schema={"type": "object", "required": ["symbol"], "properties": {"symbol": {"type": "string"}}},
            output_schema={"type": "object"},
            error_codes={"DATA_MISSING": "行情数据缺失", "INVALID_ARGUMENTS": "参数不合法"},
            data_source="iTick/AKShare/local_sample",
            handler=get_stock_price,
            mature_tool_hint="iTick /stock/tick for HK realtime; AKShare stock_zh_a_spot_em for A-share; future external MCP server compatible",
        ),
        MCPToolSpec(
            name="get_index_price",
            description="获取指数行情，默认沪深300。",
            input_schema={"type": "object", "required": [], "properties": {"symbol": {"type": "string"}}},
            output_schema={"type": "object"},
            error_codes={"DATA_MISSING": "指数行情缺失"},
            data_source="AKShare/local_sample",
            handler=get_index_price,
            mature_tool_hint="AKShare stock_zh_index_spot_em",
        ),
        MCPToolSpec(
            name="get_financial_metrics",
            description="获取估值、盈利、成长等财务指标。Day4 使用稳定边界和样例降级。",
            input_schema={"type": "object", "required": ["symbol"], "properties": {"symbol": {"type": "string"}}},
            output_schema={"type": "object"},
            error_codes={"DATA_MISSING": "财务指标缺失"},
            data_source="AKShare/local_sample",
            handler=get_financial_metrics,
            mature_tool_hint="AKShare financial APIs; Tushare adapter can be added behind same spec",
        ),
        MCPToolSpec(
            name="calculate_portfolio_risk",
            description="确定性计算组合市值、盈亏、集中度、行业集中度和风险标记。",
            input_schema={"type": "object", "required": ["holdings"], "properties": {"holdings": {"type": "array"}}},
            output_schema={"type": "object"},
            error_codes={"INVALID_ARGUMENTS": "持仓参数不合法"},
            data_source="risk_calculator",
            handler=calculate_risk,
        ),
        MCPToolSpec(
            name="search_announcements",
            description="按股票代码和关键词检索公告。优先成熟数据源，失败时降级样例公告。",
            input_schema={
                "type": "object",
                "required": ["symbol"],
                "properties": {"symbol": {"type": "string"}, "limit": {"type": "integer"}, "keywords": {"type": "array"}},
            },
            output_schema={"type": "object"},
            error_codes={"DATA_MISSING": "公告数据缺失"},
            data_source="AKShare/local_sample",
            handler=search_announcements,
            mature_tool_hint="AKShare stock_notice_report where available",
        ),
        MCPToolSpec(
            name="retrieve_evidence",
            description="检索公告风险证据片段，每条证据包含来源、标题、发布日期和原文片段。",
            input_schema={
                "type": "object",
                "required": ["symbol"],
                "properties": {"symbol": {"type": "string"}, "risk_keywords": {"type": "array"}, "limit": {"type": "integer"}},
            },
            output_schema={"type": "object"},
            error_codes={"DATA_MISSING": "证据缺失"},
            data_source="AKShare/local_sample",
            handler=retrieve_evidence,
        ),
    ]
    for spec in specs:
        if registry.get(spec.name) is None:
            registry.register(spec)
