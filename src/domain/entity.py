from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import uuid4

from src.domain.time import now_iso


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_RETRY = "waiting_retry"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TradeAction(StrEnum):
    BUY = "buy"
    ADD = "add"
    REDUCE = "reduce"
    SELL = "sell"


@dataclass(slots=True)
class User:
    user_id: str = field(default_factory=lambda: new_id("user"))
    username: str = "demo"
    role: str = "user"
    risk_preference: str = "balanced"
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)


@dataclass(slots=True)
class Holding:
    symbol: str
    shares: Decimal
    cost_price: Decimal
    holding_id: str = field(default_factory=lambda: new_id("holding"))
    name: str = ""
    buy_reason: str = ""
    buy_date: str = ""
    max_loss_limit: Decimal | None = None
    position_limit: Decimal | None = None
    industry_limit: Decimal | None = None
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)


@dataclass(slots=True)
class Portfolio:
    user_id: str
    name: str
    holdings: list[Holding] = field(default_factory=list)
    portfolio_id: str = field(default_factory=lambda: new_id("portfolio"))
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)


@dataclass(slots=True)
class WatchItem:
    user_id: str
    symbol: str
    watch_id: str = field(default_factory=lambda: new_id("watch"))
    name: str = ""
    watch_type: str = "watch_only"
    tags: list[str] = field(default_factory=list)
    price_alert_pct: Decimal | None = None
    announcement_radar: bool = True
    financial_radar: bool = True
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)


@dataclass(slots=True)
class TradeJournal:
    user_id: str
    symbol: str
    action: TradeAction
    trade_date: date
    journal_id: str = field(default_factory=lambda: new_id("journal"))
    price: Decimal | None = None
    shares: Decimal | None = None
    reason: str = ""
    review_after_days: int = 7
    created_at: str = field(default_factory=now_iso)


@dataclass(slots=True)
class AnalysisTask:
    user_id: str
    portfolio_id: str
    task_id: str = field(default_factory=lambda: new_id("task"))
    status: TaskStatus = TaskStatus.PENDING
    current_agent: str = ""
    current_action: str = ""
    completed_steps: int = 0
    total_steps: int = 0
    latest_observation: str = ""
    error_message: str = ""
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentRunRecord:
    task_id: str
    agent_name: str
    thought: str
    action: str
    observation: str
    record_id: str = field(default_factory=lambda: new_id("agent_run"))
    tool_call_id: str = ""
    created_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolCallRecord:
    task_id: str
    tool_name: str
    arguments: dict[str, Any]
    success: bool
    source: str
    call_id: str = field(default_factory=lambda: new_id("tool_call"))
    error_code: str | None = None
    error_message: str | None = None
    result_summary: str = ""
    created_at: str = field(default_factory=now_iso)


@dataclass(slots=True)
class ReportArchive:
    task_id: str
    portfolio_id: str
    markdown: str
    report_id: str = field(default_factory=lambda: new_id("report"))
    passed_guardrail: bool = False
    created_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NotificationChannel:
    user_id: str
    channel_type: str
    channel_name: str
    webhook_url: str
    channel_id: str = field(default_factory=lambda: new_id("notify_channel"))
    secret: str = ""
    enabled: bool = True
    event_types: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)


@dataclass(slots=True)
class NotificationRecord:
    channel_id: str
    event_type: str
    title: str
    content: str
    record_id: str = field(default_factory=lambda: new_id("notify_record"))
    status: str = "pending"
    error_message: str = ""
    retry_count: int = 0
    sent_at: str = ""
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ScheduledJob:
    user_id: str
    job_type: str
    target_id: str
    job_id: str = field(default_factory=lambda: new_id("schedule"))
    enabled: bool = False
    cron: str = ""
    status: str = "paused"
    last_skip_reason: str = ""
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
