from __future__ import annotations

from typing import Any

from src.app.service.announcement_rag_service import AnnouncementRAGService
from src.domain.tool import MCPToolResult, MCPToolSpec
from src.infra.adapter.mcp.registry import MCPToolRegistry


def register_announcement_tools(registry: MCPToolRegistry, rag_service: AnnouncementRAGService) -> None:
    def ingest_announcements(arguments: dict[str, Any]) -> MCPToolResult:
        result = rag_service.ingest_symbol_announcements(
            symbol=arguments["symbol"],
            limit=arguments.get("limit", 10),
            keywords=arguments.get("keywords"),
        )
        return MCPToolResult(success=True, data=result, source="announcement_rag")

    def retrieve_announcement_evidence(arguments: dict[str, Any]) -> MCPToolResult:
        result = rag_service.retrieve_evidence(
            symbol=arguments["symbol"],
            risk_keywords=arguments.get("risk_keywords"),
            query=arguments.get("query"),
            limit=arguments.get("limit", 5),
            auto_ingest=arguments.get("auto_ingest", True),
        )
        return MCPToolResult(success=True, data=result, source="announcement_rag")

    def analyze_announcement_risk(arguments: dict[str, Any]) -> MCPToolResult:
        result = rag_service.analyze_symbol(
            symbol=arguments["symbol"],
            company_name=arguments.get("company_name", ""),
            limit=arguments.get("limit", 5),
        )
        return MCPToolResult(success=True, data=result, source="announcement_rag")

    specs = [
        MCPToolSpec(
            name="ingest_announcements",
            description="公告入库工具。按股票代码抓取公告、切块、风险关键词标注并写入 Chroma。",
            input_schema={
                "type": "object",
                "required": ["symbol"],
                "properties": {"symbol": {"type": "string"}, "limit": {"type": "integer"}, "keywords": {"type": "array"}},
            },
            output_schema={"type": "object"},
            error_codes={"INGEST_FAILED": "公告入库失败"},
            data_source="AKShare/local_sample + Chroma",
            handler=ingest_announcements,
            mature_tool_hint="Can be split into an independent announcement MCP server later",
        ),
        MCPToolSpec(
            name="retrieve_announcement_evidence",
            description="RAG 证据检索工具。基于股票代码、风险关键词和向量检索返回公告证据片段。",
            input_schema={
                "type": "object",
                "required": ["symbol"],
                "properties": {
                    "symbol": {"type": "string"},
                    "risk_keywords": {"type": "array"},
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                    "auto_ingest": {"type": "boolean"},
                },
            },
            output_schema={"type": "object"},
            error_codes={"EVIDENCE_MISSING": "公告证据缺失"},
            data_source="Chroma",
            handler=retrieve_announcement_evidence,
        ),
        MCPToolSpec(
            name="analyze_announcement_risk",
            description="公告风险识别工具。输出减持、诉讼、问询、业绩预亏等风险事件及证据来源。",
            input_schema={
                "type": "object",
                "required": ["symbol"],
                "properties": {"symbol": {"type": "string"}, "company_name": {"type": "string"}, "limit": {"type": "integer"}},
            },
            output_schema={"type": "object"},
            error_codes={"ANALYSIS_FAILED": "公告风险识别失败"},
            data_source="announcement_rag",
            handler=analyze_announcement_risk,
        ),
    ]
    for spec in specs:
        if registry.get(spec.name) is None:
            registry.register(spec)
