from __future__ import annotations

from typing import Any

from src.domain.entity import AgentRunRecord, Portfolio
from src.infra.adapter.mcp import MCPToolRegistry
from src.infra.repo.mem import MemUnitOfWork


class AnnouncementAgent:
    name = "AnnouncementAgent"

    def __init__(self, registry: MCPToolRegistry, uow: MemUnitOfWork) -> None:
        self.registry = registry
        self.uow = uow

    def run(self, task_id: str, portfolio: Portfolio) -> dict[str, Any]:
        self._record(
            task_id,
            thought="公告风险需要先入库再检索证据，避免只凭标题下结论。",
            action="announcement_rag_start",
            observation="开始逐个持仓执行公告 RAG 风险识别。",
        )
        symbol_results = []
        risk_events = []
        for holding in portfolio.holdings[:10]:
            result = self.registry.call(
                "analyze_announcement_risk",
                {"symbol": holding.symbol, "company_name": holding.name, "limit": 5},
                task_id=task_id,
            ).to_dict()
            symbol_results.append(result)
            if result.get("success"):
                risk_events.extend(result.get("data", {}).get("risk_events", []))

        summary = _summarize_announcement_result(risk_events)
        self._record(
            task_id,
            thought="公告风险识别完成，只输出风险提示和证据来源，不给出买卖建议。",
            action="announcement_summary",
            observation=summary,
        )
        return {
            "summary": summary,
            "risk_event_count": len(risk_events),
            "risk_events": risk_events,
            "symbols": symbol_results,
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


def _summarize_announcement_result(risk_events: list[dict[str, Any]]) -> str:
    if not risk_events:
        return "未检索到命中预设风险关键词的公告事件。"
    labels: dict[str, int] = {}
    for event in risk_events:
        label = str(event.get("risk_label", "未知风险"))
        labels[label] = labels.get(label, 0) + 1
    detail = "；".join(f"{label} {count} 条" for label, count in sorted(labels.items()))
    return f"检索到公告风险事件 {len(risk_events)} 条：{detail}。"
