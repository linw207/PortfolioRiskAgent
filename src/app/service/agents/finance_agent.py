from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Any

from src.domain.entity import AgentRunRecord, Portfolio
from src.infra.adapter.mcp import MCPToolRegistry
from src.infra.repo.mem import MemUnitOfWork


class FinanceAgent:
    name = "FinanceAgent"

    def __init__(self, registry: MCPToolRegistry, uow: MemUnitOfWork) -> None:
        self.registry = registry
        self.uow = uow

    def run(self, task_id: str, portfolio: Portfolio) -> dict[str, Any]:
        holdings = [_holding_to_tool_payload(item) for item in portfolio.holdings[:10]]
        self._record(
            task_id,
            thought="需要先调用确定性风险计算工具，避免模型自行编造金融指标。",
            action="calculate_portfolio_risk",
            observation="开始计算组合市值、盈亏、集中度和风险标记。",
        )
        risk = self.registry.call("calculate_portfolio_risk", {"holdings": holdings}, task_id=task_id).to_dict()

        quotes: dict[str, Any] = {}
        metrics: dict[str, Any] = {}
        for holding in portfolio.holdings[:10]:
            quotes[holding.symbol] = self.registry.call("get_stock_price", {"symbol": holding.symbol}, task_id=task_id).to_dict()
            metrics[holding.symbol] = self.registry.call(
                "get_financial_metrics",
                {"symbol": holding.symbol},
                task_id=task_id,
            ).to_dict()

        summary = _summarize_finance_result(risk)
        self._record(
            task_id,
            thought="金融工具调用完成，只解释风险指标，不输出任何操作建议。",
            action="finance_summary",
            observation=summary,
        )
        return {
            "summary": summary,
            "risk": risk,
            "quotes": quotes,
            "financial_metrics": metrics,
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


def _holding_to_tool_payload(holding: Any) -> dict[str, Any]:
    payload = asdict(holding)
    for key, value in list(payload.items()):
        if isinstance(value, Decimal):
            payload[key] = float(value)
    return payload


def _summarize_finance_result(risk: dict[str, Any]) -> str:
    if not risk.get("success"):
        return f"组合风险计算失败：{risk.get('error_message') or '未知错误'}"
    data = risk.get("data", {})
    total_market_value = data.get("total_market_value", 0)
    total_pnl = data.get("total_pnl", 0)
    highest_weight = data.get("highest_position_weight", 0)
    flags = data.get("risk_flags", [])
    return (
        f"组合总市值 {total_market_value:.2f} 元；"
        f"总盈亏 {total_pnl:.2f} 元；"
        f"第一大持仓占比 {highest_weight:.1%}；"
        f"风险标记 {len(flags)} 个。"
    )
