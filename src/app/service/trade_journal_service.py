from __future__ import annotations

from typing import Any

from src.app.service.validation import normalize_symbol, parse_date, to_decimal
from src.domain.entity import TradeAction, TradeJournal
from src.infra.repo.mem import MemUnitOfWork


class TradeJournalService:
    def __init__(self, uow: MemUnitOfWork) -> None:
        self.uow = uow

    def add_journal(self, user_id: str, payload: dict[str, Any]) -> TradeJournal:
        action = TradeAction(payload["action"])
        reason = str(payload.get("reason", ""))[:500]
        if action in {TradeAction.BUY, TradeAction.ADD} and not reason:
            raise ValueError("买入和加仓必须填写操作理由")
        journal = TradeJournal(
            user_id=user_id,
            symbol=normalize_symbol(payload["symbol"]),
            action=action,
            trade_date=parse_date(payload["trade_date"], "交易日期"),
            price=to_decimal(payload["price"], "成交价格") if payload.get("price") else None,
            shares=to_decimal(payload["shares"], "成交数量") if payload.get("shares") else None,
            reason=reason,
            review_after_days=int(payload.get("review_after_days", 7)),
        )
        return self.uow.trade_journals.save(journal)

    def list_journals(self, user_id: str, symbol: str | None = None) -> list[TradeJournal]:
        normalized = normalize_symbol(symbol) if symbol else None
        return self.uow.trade_journals.list_by_user(user_id, symbol=normalized)
