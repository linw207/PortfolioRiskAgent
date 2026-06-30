from __future__ import annotations

from typing import Any

from src.domain.entity import AgentRunRecord, Portfolio
from src.infra.adapter.mcp import MCPToolRegistry
from src.infra.repo.mem import MemUnitOfWork


class ReviewAgent:
    name = "ReviewAgent"

    def __init__(self, registry: MCPToolRegistry, uow: MemUnitOfWork) -> None:
        self.registry = registry
        self.uow = uow

    def run(self, task_id: str, portfolio: Portfolio) -> dict[str, Any]:
        self._record(
            task_id,
            thought="复盘需要把用户原始交易理由与当前行情、财务、公告和历史记忆做对照。",
            action="trade_review_start",
            observation="开始逐持仓查询交易日志并执行 Reflection。",
        )
        reviews = []
        questions = []
        for holding in portfolio.holdings[:10]:
            journals_result = self.registry.call(
                "search_trade_journals",
                {"user_id": portfolio.user_id, "symbol": holding.symbol, "limit": 5},
                task_id=task_id,
            ).to_dict()
            journals = journals_result.get("data", {}).get("journals", []) if journals_result.get("success") else []
            if not journals:
                question = f"请人工复核 {holding.symbol}：当前持仓缺少交易日志，无法对照原买入理由。"
                questions.append(question)
                reviews.append({"symbol": holding.symbol, "journal_reviews": [], "questions": [question]})
                continue

            quote = self.registry.call("get_stock_price", {"symbol": holding.symbol}, task_id=task_id).to_dict()
            metrics = self.registry.call("get_financial_metrics", {"symbol": holding.symbol}, task_id=task_id).to_dict()
            announcements = self.registry.call(
                "analyze_announcement_risk",
                {"symbol": holding.symbol, "company_name": holding.name, "limit": 3},
                task_id=task_id,
            ).to_dict()
            memories = self.registry.call(
                "retrieve_risk_memory",
                {"user_id": portfolio.user_id, "symbol": holding.symbol, "query": f"{holding.symbol} 交易复盘 风险", "limit": 3},
                task_id=task_id,
            ).to_dict()

            current_facts = {
                "quote": quote.get("data", {}) if quote.get("success") else {},
                "financial_metrics": metrics.get("data", {}) if metrics.get("success") else {},
                "announcement_events": announcements.get("data", {}).get("risk_events", []) if announcements.get("success") else [],
            }
            historical_memories = memories.get("data", {}).get("items", []) if memories.get("success") else []
            journal_reviews = []
            for journal in journals:
                reflection = self.registry.call(
                    "reflect_trade_journal",
                    {
                        "journal": journal,
                        "current_facts": current_facts,
                        "historical_memories": historical_memories,
                    },
                    task_id=task_id,
                ).to_dict()
                if not reflection.get("success"):
                    continue
                data = reflection["data"]
                journal_reviews.append(data)
                questions.extend(data.get("questions", []))
                self._save_memory(task_id, portfolio.user_id, holding.symbol, data)
            reviews.append({"symbol": holding.symbol, "journal_reviews": journal_reviews, "questions": [q for q in questions if holding.symbol in q]})

        summary = _summarize_reviews(questions)
        self._record(
            task_id,
            thought="复盘完成，输出待人工复核问题并保存历史记忆。",
            action="trade_review_summary",
            observation=summary,
        )
        return {
            "summary": summary,
            "question_count": len(questions),
            "questions": questions,
            "reviews": reviews,
        }

    def _save_memory(self, task_id: str, user_id: str, symbol: str, reflection: dict[str, Any]) -> None:
        text = (
            f"{symbol} 交易复盘："
            f"信号={';'.join(reflection.get('signals', [])) or '无强规则冲突'}；"
            f"问题={';'.join(reflection.get('questions', []))}"
        )
        self.registry.call(
            "save_risk_memory",
            {
                "user_id": user_id,
                "symbol": symbol,
                "task_id": task_id,
                "text": text[:1000],
                "memory_type": "trade_review",
            },
            task_id=task_id,
        )

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


def _summarize_reviews(questions: list[str]) -> str:
    if not questions:
        return "交易复盘未生成待人工复核问题。"
    return f"交易复盘生成待人工复核问题 {len(questions)} 个。"
