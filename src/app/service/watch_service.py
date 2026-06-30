from __future__ import annotations

from typing import Any

from src.app.service.validation import normalize_symbol, optional_ratio
from src.domain.entity import WatchItem
from src.infra.repo.mem import MemUnitOfWork


class WatchService:
    def __init__(self, uow: MemUnitOfWork) -> None:
        self.uow = uow

    def add_watch_item(self, user_id: str, payload: dict[str, Any]) -> WatchItem:
        symbol = normalize_symbol(payload["symbol"])
        if any(item.symbol == symbol for item in self.uow.watch_items.list_by_user(user_id)):
            raise ValueError("该股票已在关注池中")
        item = WatchItem(
            user_id=user_id,
            symbol=symbol,
            name=str(payload.get("name", ""))[:50],
            watch_type=payload.get("watch_type", "watch_only"),
            tags=[str(tag)[:10] for tag in payload.get("tags", [])[:5]],
            price_alert_pct=optional_ratio(payload.get("price_alert_pct", "0.05"), "涨跌幅提醒阈值"),
            announcement_radar=bool(payload.get("announcement_radar", True)),
            financial_radar=bool(payload.get("financial_radar", True)),
        )
        return self.uow.watch_items.save(item)

    def list_watch_items(self, user_id: str) -> list[WatchItem]:
        return self.uow.watch_items.list_by_user(user_id)

    def delete_watch_item(self, watch_id: str) -> bool:
        return self.uow.watch_items.delete(watch_id)
