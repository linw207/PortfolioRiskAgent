from __future__ import annotations

from dataclasses import asdict
from datetime import date
from decimal import Decimal
import hashlib
from typing import Any

from src.app.service.validation import normalize_symbol
from src.app.service.vector_memory_service import VectorMemoryService
from src.domain.entity import TradeAction, TradeJournal
from src.domain.time import now_iso
from src.infra.repo.mem import MemUnitOfWork


class TradeReviewService:
    def __init__(self, uow: MemUnitOfWork, vector_memory: VectorMemoryService) -> None:
        self.uow = uow
        self.vector_memory = vector_memory

    def search_trade_journals(self, user_id: str, symbol: str | None = None, limit: int = 10) -> dict[str, Any]:
        normalized = normalize_symbol(symbol) if symbol else None
        journals = self.uow.trade_journals.list_by_user(user_id, normalized)
        journals = sorted(journals, key=lambda item: item.trade_date, reverse=True)[:limit]
        return {
            "user_id": user_id,
            "symbol": normalized,
            "journals": [serialize_journal(item) for item in journals],
        }

    def save_risk_memory(
        self,
        user_id: str,
        symbol: str,
        task_id: str,
        text: str,
        memory_type: str = "trade_review",
    ) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        memory_id = "mem_" + hashlib.sha256(f"{task_id}|{normalized}|{text}".encode("utf-8")).hexdigest()[:20]
        memory = {
            "memory_id": memory_id,
            "user_id": user_id,
            "symbol": normalized,
            "task_id": task_id,
            "created_at": now_iso(),
            "memory_type": memory_type,
            "text": text,
        }
        return self.vector_memory.upsert_agent_memory([memory])

    def retrieve_risk_memory(
        self,
        user_id: str,
        symbol: str | None = None,
        query: str = "交易复盘 风险 记忆",
        limit: int = 5,
    ) -> dict[str, Any]:
        normalized = normalize_symbol(symbol) if symbol else None
        return self.vector_memory.search_agent_memory(query=query, user_id=user_id, symbol=normalized, limit=limit)

    def build_working_memory(self, user_id: str, symbol: str, limit: int = 5) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        journals = self.search_trade_journals(user_id, normalized, limit)
        memories = self.retrieve_risk_memory(user_id, normalized, f"{normalized} 交易复盘 风险", limit)
        return {
            "user_id": user_id,
            "symbol": normalized,
            "trade_journals": journals["journals"],
            "historical_memories": memories.get("items", []),
        }

    def reflect_trade_journal(
        self,
        journal: dict[str, Any],
        current_facts: dict[str, Any],
        historical_memories: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        reason = str(journal.get("reason", ""))
        symbol = str(journal.get("symbol", ""))
        action = str(journal.get("action", ""))
        questions = []
        signals = []

        quote = current_facts.get("quote", {})
        metrics = current_facts.get("financial_metrics", {})
        announcement_events = current_facts.get("announcement_events", [])

        change_pct = _to_float(quote.get("change_pct"))
        net_profit_growth = _to_float(metrics.get("net_profit_growth"))
        revenue_growth = _to_float(metrics.get("revenue_growth"))

        if action in {TradeAction.BUY.value, TradeAction.ADD.value} and not reason:
            questions.append(f"请人工复核 {symbol} 的买入/加仓理由：原交易日志缺少明确理由，当前无法对照事实验证。")

        if _contains_any(reason, ["成长", "增长", "业绩", "盈利"]) and (net_profit_growth < 0 or revenue_growth < 0):
            signals.append("原理由关注成长/业绩，但当前收入或净利润增速为负。")
            questions.append(f"请人工复核 {symbol} 的成长假设：买入理由提到成长或业绩，但当前财务增速出现压力。")

        if _contains_any(reason, ["低估", "价值", "长期", "稳定"]) and change_pct <= -0.03:
            signals.append("原理由偏长期/价值，但当前价格短期回撤超过 3%。")
            questions.append(f"请人工复核 {symbol} 的持仓假设：价值/长期理由是否仍能覆盖近期价格回撤和基本面变化。")

        for event in announcement_events:
            label = event.get("risk_label", "公告风险")
            title = event.get("evidence", {}).get("title", "")
            signals.append(f"公告风险：{label}")
            questions.append(f"请人工复核 {symbol} 的公告风险：{label}，证据公告《{title}》。")

        if historical_memories:
            signals.append(f"检索到历史记忆 {len(historical_memories)} 条，可用于对照此前复盘结论。")

        if not questions:
            questions.append(f"请人工复核 {symbol}：当前未命中强规则冲突，但仍需确认交易理由与最新行情、财务和公告事实是否一致。")

        return {
            "symbol": symbol,
            "journal_id": journal.get("journal_id", ""),
            "action": action,
            "reason": reason,
            "signals": signals,
            "questions": questions,
            "needs_human_review": True,
        }


def serialize_journal(journal: TradeJournal) -> dict[str, Any]:
    payload = asdict(journal)
    for key, value in list(payload.items()):
        if isinstance(value, Decimal):
            payload[key] = float(value)
        elif isinstance(value, date):
            payload[key] = value.isoformat()
        elif isinstance(value, TradeAction):
            payload[key] = value.value
    return payload


def _contains_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
