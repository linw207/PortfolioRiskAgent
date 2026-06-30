from __future__ import annotations

from typing import Any

from src.app.service.trade_review_service import TradeReviewService
from src.domain.tool import MCPToolResult, MCPToolSpec
from src.infra.adapter.mcp.registry import MCPToolRegistry


def register_review_tools(registry: MCPToolRegistry, review_service: TradeReviewService) -> None:
    def search_trade_journals(arguments: dict[str, Any]) -> MCPToolResult:
        result = review_service.search_trade_journals(
            user_id=arguments["user_id"],
            symbol=arguments.get("symbol"),
            limit=arguments.get("limit", 10),
        )
        return MCPToolResult(success=True, data=result, source="trade_journal_repository")

    def retrieve_risk_memory(arguments: dict[str, Any]) -> MCPToolResult:
        result = review_service.retrieve_risk_memory(
            user_id=arguments["user_id"],
            symbol=arguments.get("symbol"),
            query=arguments.get("query", "交易复盘 风险 记忆"),
            limit=arguments.get("limit", 5),
        )
        return MCPToolResult(success=True, data=result, source="agent_memory_vector")

    def save_risk_memory(arguments: dict[str, Any]) -> MCPToolResult:
        result = review_service.save_risk_memory(
            user_id=arguments["user_id"],
            symbol=arguments["symbol"],
            task_id=arguments["task_id"],
            text=arguments["text"],
            memory_type=arguments.get("memory_type", "trade_review"),
        )
        return MCPToolResult(success=True, data=result, source="agent_memory_vector")

    def reflect_trade_journal(arguments: dict[str, Any]) -> MCPToolResult:
        result = review_service.reflect_trade_journal(
            journal=arguments["journal"],
            current_facts=arguments.get("current_facts", {}),
            historical_memories=arguments.get("historical_memories", []),
        )
        return MCPToolResult(success=True, data=result, source="reflection_rules")

    specs = [
        MCPToolSpec(
            name="search_trade_journals",
            description="查询用户交易日志，可按股票代码过滤，用于复盘 Agent 对照买入理由。",
            input_schema={
                "type": "object",
                "required": ["user_id"],
                "properties": {"user_id": {"type": "string"}, "symbol": {"type": "string"}, "limit": {"type": "integer"}},
            },
            output_schema={"type": "object"},
            error_codes={"TRADE_JOURNAL_MISSING": "交易日志缺失"},
            data_source="MongoDB/memory trade_journals",
            handler=search_trade_journals,
        ),
        MCPToolSpec(
            name="retrieve_risk_memory",
            description="检索历史风险记忆和复盘摘要，基于 Chroma agent_memory 集合。",
            input_schema={
                "type": "object",
                "required": ["user_id"],
                "properties": {
                    "user_id": {"type": "string"},
                    "symbol": {"type": "string"},
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
            output_schema={"type": "object"},
            error_codes={"MEMORY_MISSING": "历史记忆缺失"},
            data_source="Chroma agent_memory",
            handler=retrieve_risk_memory,
        ),
        MCPToolSpec(
            name="save_risk_memory",
            description="保存历史风险事件或复盘摘要到 Chroma agent_memory 集合。",
            input_schema={
                "type": "object",
                "required": ["user_id", "symbol", "task_id", "text"],
                "properties": {
                    "user_id": {"type": "string"},
                    "symbol": {"type": "string"},
                    "task_id": {"type": "string"},
                    "text": {"type": "string"},
                    "memory_type": {"type": "string"},
                },
            },
            output_schema={"type": "object"},
            error_codes={"MEMORY_SAVE_FAILED": "历史记忆保存失败"},
            data_source="Chroma agent_memory",
            handler=save_risk_memory,
        ),
        MCPToolSpec(
            name="reflect_trade_journal",
            description="Reflection 审查工具，对照交易理由、当前事实和历史记忆，生成待人工复核问题。",
            input_schema={
                "type": "object",
                "required": ["journal"],
                "properties": {
                    "journal": {"type": "object"},
                    "current_facts": {"type": "object"},
                    "historical_memories": {"type": "array"},
                },
            },
            output_schema={"type": "object"},
            error_codes={"REFLECTION_FAILED": "复盘审查失败"},
            data_source="reflection_rules",
            handler=reflect_trade_journal,
        ),
    ]
    for spec in specs:
        if registry.get(spec.name) is None:
            registry.register(spec)
