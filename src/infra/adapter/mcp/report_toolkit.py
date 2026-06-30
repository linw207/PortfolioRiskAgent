from __future__ import annotations

from typing import Any

from src.app.service.report_service import ReportService
from src.domain.tool import MCPToolResult, MCPToolSpec
from src.infra.adapter.mcp.registry import MCPToolRegistry


def register_report_tools(registry: MCPToolRegistry, report_service: ReportService) -> None:
    def render_report(arguments: dict[str, Any]) -> MCPToolResult:
        markdown = report_service.render_report(arguments["portfolio"], arguments.get("sections", {}))
        return MCPToolResult(success=True, data={"markdown": markdown}, source="report_template")

    def guardrail_check(arguments: dict[str, Any]) -> MCPToolResult:
        result = report_service.guardrail_check(arguments["markdown"], use_model=arguments.get("use_model", True))
        return MCPToolResult(success=True, data=result, source="report_guardrail")

    def rewrite_violations(arguments: dict[str, Any]) -> MCPToolResult:
        result = report_service.guardrail_check(arguments["markdown"], use_model=False)
        return MCPToolResult(success=True, data={"markdown": result["rewritten_markdown"], "violations": result["violations"]}, source="report_guardrail")

    def save_report(arguments: dict[str, Any]) -> MCPToolResult:
        report = report_service.save_report(
            task_id=arguments["task_id"],
            portfolio_id=arguments["portfolio_id"],
            markdown=arguments["markdown"],
            guardrail=arguments["guardrail"],
        )
        return MCPToolResult(
            success=True,
            data={"report_id": report.report_id, "task_id": report.task_id, "passed_guardrail": report.passed_guardrail},
            source="report_archive",
        )

    def get_report(arguments: dict[str, Any]) -> MCPToolResult:
        report = report_service.get_report_by_task(arguments["task_id"])
        if report is None:
            return MCPToolResult(
                success=False,
                data={},
                source="report_archive",
                error_code="REPORT_NOT_FOUND",
                error_message="报告不存在",
            )
        return MCPToolResult(
            success=True,
            data={
                "report_id": report.report_id,
                "task_id": report.task_id,
                "portfolio_id": report.portfolio_id,
                "markdown": report.markdown,
                "passed_guardrail": report.passed_guardrail,
                "created_at": report.created_at,
                "metadata": report.metadata,
            },
            source="report_archive",
        )

    specs = [
        MCPToolSpec(
            name="render_report",
            description="生成完整 Markdown 持仓体检报告，包含金融、公告、复盘和数据来源。",
            input_schema={"type": "object", "required": ["portfolio"], "properties": {"portfolio": {"type": "object"}, "sections": {"type": "object"}}},
            output_schema={"type": "object"},
            error_codes={"RENDER_FAILED": "报告渲染失败"},
            data_source="report_template",
            handler=render_report,
        ),
        MCPToolSpec(
            name="guardrail_check",
            description="报告安全审查，检查买卖建议、目标价、收益承诺等违规表达，并返回改写文本。",
            input_schema={
                "type": "object",
                "required": ["markdown"],
                "properties": {"markdown": {"type": "string"}, "use_model": {"type": "boolean"}},
            },
            output_schema={"type": "object"},
            error_codes={"GUARDRAIL_FAILED": "安全审查失败"},
            data_source="report_guardrail",
            handler=guardrail_check,
        ),
        MCPToolSpec(
            name="rewrite_report_violations",
            description="对报告中的违规表达进行规则改写。",
            input_schema={"type": "object", "required": ["markdown"], "properties": {"markdown": {"type": "string"}}},
            output_schema={"type": "object"},
            error_codes={"REWRITE_FAILED": "违规表达改写失败"},
            data_source="report_guardrail",
            handler=rewrite_violations,
        ),
        MCPToolSpec(
            name="save_report",
            description="保存报告和安全审查结果到 report_archives。",
            input_schema={
                "type": "object",
                "required": ["task_id", "portfolio_id", "markdown", "guardrail"],
                "properties": {
                    "task_id": {"type": "string"},
                    "portfolio_id": {"type": "string"},
                    "markdown": {"type": "string"},
                    "guardrail": {"type": "object"},
                },
            },
            output_schema={"type": "object"},
            error_codes={"SAVE_FAILED": "报告保存失败"},
            data_source="report_archive",
            handler=save_report,
        ),
        MCPToolSpec(
            name="get_report",
            description="按任务 ID 查询已归档报告。",
            input_schema={"type": "object", "required": ["task_id"], "properties": {"task_id": {"type": "string"}}},
            output_schema={"type": "object"},
            error_codes={"REPORT_NOT_FOUND": "报告不存在"},
            data_source="report_archive",
            handler=get_report,
        ),
    ]
    for spec in specs:
        if registry.get(spec.name) is None:
            registry.register(spec)
