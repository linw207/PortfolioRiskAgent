from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from src.domain.entity import (
    AgentRunRecord,
    AnalysisTask,
    Holding,
    NotificationChannel,
    NotificationRecord,
    Portfolio,
    ReportArchive,
    ScheduledJob,
    TaskStatus,
    ToolCallRecord,
    TradeAction,
    TradeJournal,
    User,
    WatchItem,
)


def _clean(document: dict[str, Any]) -> dict[str, Any]:
    data = dict(document)
    data.pop("_id", None)
    return data


def _decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    return Decimal(str(value))


def decode_user(document: dict[str, Any]) -> User:
    return User(**_clean(document))


def decode_holding(document: dict[str, Any]) -> Holding:
    data = _clean(document)
    data["shares"] = _decimal(data["shares"])
    data["cost_price"] = _decimal(data["cost_price"])
    data["max_loss_limit"] = _decimal(data.get("max_loss_limit"))
    data["position_limit"] = _decimal(data.get("position_limit"))
    data["industry_limit"] = _decimal(data.get("industry_limit"))
    return Holding(**data)


def decode_portfolio(document: dict[str, Any]) -> Portfolio:
    data = _clean(document)
    data["holdings"] = [decode_holding(item) for item in data.get("holdings", [])]
    return Portfolio(**data)


def decode_watch_item(document: dict[str, Any]) -> WatchItem:
    data = _clean(document)
    data["price_alert_pct"] = _decimal(data.get("price_alert_pct"))
    return WatchItem(**data)


def decode_trade_journal(document: dict[str, Any]) -> TradeJournal:
    data = _clean(document)
    data["action"] = TradeAction(data["action"])
    data["trade_date"] = date.fromisoformat(data["trade_date"])
    data["price"] = _decimal(data.get("price"))
    data["shares"] = _decimal(data.get("shares"))
    return TradeJournal(**data)


def decode_analysis_task(document: dict[str, Any]) -> AnalysisTask:
    data = _clean(document)
    data["status"] = TaskStatus(data["status"])
    return AnalysisTask(**data)


def decode_agent_run(document: dict[str, Any]) -> AgentRunRecord:
    return AgentRunRecord(**_clean(document))


def decode_tool_call(document: dict[str, Any]) -> ToolCallRecord:
    return ToolCallRecord(**_clean(document))


def decode_report(document: dict[str, Any]) -> ReportArchive:
    return ReportArchive(**_clean(document))


def decode_notification_channel(document: dict[str, Any]) -> NotificationChannel:
    return NotificationChannel(**_clean(document))


def decode_notification_record(document: dict[str, Any]) -> NotificationRecord:
    return NotificationRecord(**_clean(document))


def decode_scheduled_job(document: dict[str, Any]) -> ScheduledJob:
    return ScheduledJob(**_clean(document))
