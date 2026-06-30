from __future__ import annotations

from typing import Any

from src.domain.entity import AgentRunRecord, Portfolio
from src.domain.tool import MCPToolResult, MCPToolSpec
from src.infra.adapter.mcp import MCPToolRegistry
from src.infra.repo.mem import MemUnitOfWork


class OrchestratorAgent:
    name = "OrchestratorAgent"

    def __init__(self, registry: MCPToolRegistry, uow: MemUnitOfWork) -> None:
        self.registry = registry
        self.uow = uow

    def register_professional_agents(self, finance_runner: Any) -> None:
        if self.registry.get("run_finance_agent") is not None:
            return

        def run_finance(arguments: dict[str, Any]) -> MCPToolResult:
            portfolio = arguments["portfolio"]
            task_id = arguments.get("task_id", "")
            result = finance_runner(task_id, portfolio)
            return MCPToolResult(success=True, data=result, source="FinanceAgent")

        self.registry.register(
            MCPToolSpec(
                name="run_finance_agent",
                description="调用金融分析 Agent。主控 Agent 将专业 Agent 作为工具调用。",
                input_schema={
                    "type": "object",
                    "required": ["portfolio", "task_id"],
                    "properties": {
                        "portfolio": {"type": "object"},
                        "task_id": {"type": "string"},
                    },
                },
                output_schema={"type": "object"},
                error_codes={"FINANCE_AGENT_FAILED": "金融分析 Agent 执行失败"},
                data_source="internal_agent",
                handler=run_finance,
                mature_tool_hint="Internal agent-as-tool boundary; can become MCP server later",
            )
        )

    def run(self, task_id: str, portfolio: Portfolio) -> dict[str, Any]:
        self._record(
            task_id,
            thought="持仓体检必须先完成金融分析，公告和复盘留到后续阶段动态扩展。",
            action="run_finance_agent",
            observation="准备将 FinanceAgent 作为专业 Agent 工具调用。",
        )
        result = self.registry.call(
            "run_finance_agent",
            {"task_id": task_id, "portfolio": portfolio},
            task_id=task_id,
        ).to_dict()
        observation = "FinanceAgent 执行完成。" if result.get("success") else f"FinanceAgent 执行失败：{result.get('error_message')}"
        self._record(
            task_id,
            thought="主控 Agent 已获得金融分析结果，Day6 到此停止，不扩展公告/RAG/报告。",
            action="orchestrator_summary",
            observation=observation,
        )
        return {
            "finance": result,
            "next_agents": [
                {"agent": "AnnouncementAgent", "status": "pending_day7"},
                {"agent": "ReviewAgent", "status": "pending_day8"},
                {"agent": "ReportAgent", "status": "pending_day9"},
            ],
        }

    def _record(self, task_id: str, thought: str, action: str, observation: str) -> AgentRunRecord:
        return self.uow.agent_runs.save(
            AgentRunRecord(
                task_id=task_id,
                agent_name=self.name,
                thought=thought,
                action=action,
                observation=observation[:1000],
            )
        )
