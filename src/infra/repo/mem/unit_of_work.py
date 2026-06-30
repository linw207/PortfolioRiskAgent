from __future__ import annotations

from dataclasses import fields
from typing import Any, Generic, TypeVar

from src.domain.entity import (
    AgentRunRecord,
    AnalysisTask,
    NotificationChannel,
    NotificationRecord,
    Portfolio,
    ReportArchive,
    ScheduledJob,
    ToolCallRecord,
    TradeJournal,
    User,
    WatchItem,
)


T = TypeVar("T")


class MemCollection(Generic[T]):
    def __init__(self, id_field: str) -> None:
        self.id_field = id_field
        self.items: dict[str, T] = {}

    def save(self, item: T) -> T:
        self.items[getattr(item, self.id_field)] = item
        return item

    def get(self, item_id: str) -> T | None:
        return self.items.get(item_id)

    def list_all(self) -> list[T]:
        return list(self.items.values())

    def list_where(self, **conditions: Any) -> list[T]:
        return [
            item
            for item in self.items.values()
            if all(getattr(item, key, None) == value for key, value in conditions.items())
        ]

    def delete(self, item_id: str) -> bool:
        return self.items.pop(item_id, None) is not None


class MemUserRepository:
    def __init__(self, collection: MemCollection[User]) -> None:
        self.collection = collection

    def save(self, user: User) -> User:
        return self.collection.save(user)

    def get(self, user_id: str) -> User | None:
        return self.collection.get(user_id)


class MemPortfolioRepository:
    def __init__(self, collection: MemCollection[Portfolio]) -> None:
        self.collection = collection

    def save(self, portfolio: Portfolio) -> Portfolio:
        return self.collection.save(portfolio)

    def get(self, portfolio_id: str) -> Portfolio | None:
        return self.collection.get(portfolio_id)

    def list_by_user(self, user_id: str) -> list[Portfolio]:
        return self.collection.list_where(user_id=user_id)


class MemWatchRepository:
    def __init__(self, collection: MemCollection[WatchItem]) -> None:
        self.collection = collection

    def save(self, item: WatchItem) -> WatchItem:
        return self.collection.save(item)

    def list_by_user(self, user_id: str) -> list[WatchItem]:
        return self.collection.list_where(user_id=user_id)

    def delete(self, watch_id: str) -> bool:
        return self.collection.delete(watch_id)


class MemTradeJournalRepository:
    def __init__(self, collection: MemCollection[TradeJournal]) -> None:
        self.collection = collection

    def save(self, journal: TradeJournal) -> TradeJournal:
        return self.collection.save(journal)

    def list_by_user(self, user_id: str, symbol: str | None = None) -> list[TradeJournal]:
        items = self.collection.list_where(user_id=user_id)
        if symbol:
            return [item for item in items if item.symbol == symbol]
        return items


class MemAnalysisTaskRepository:
    def __init__(self, collection: MemCollection[AnalysisTask]) -> None:
        self.collection = collection

    def save(self, task: AnalysisTask) -> AnalysisTask:
        return self.collection.save(task)

    def get(self, task_id: str) -> AnalysisTask | None:
        return self.collection.get(task_id)

    def list_by_user(self, user_id: str) -> list[AnalysisTask]:
        return self.collection.list_where(user_id=user_id)

    def list_all(self) -> list[AnalysisTask]:
        return self.collection.list_all()


class MemAgentRunRepository:
    def __init__(self, collection: MemCollection[AgentRunRecord]) -> None:
        self.collection = collection

    def save(self, record: AgentRunRecord) -> AgentRunRecord:
        return self.collection.save(record)

    def list_by_task(self, task_id: str) -> list[AgentRunRecord]:
        return self.collection.list_where(task_id=task_id)


class MemToolCallRepository:
    def __init__(self, collection: MemCollection[ToolCallRecord]) -> None:
        self.collection = collection

    def save(self, record: ToolCallRecord) -> ToolCallRecord:
        return self.collection.save(record)

    def list_by_task(self, task_id: str) -> list[ToolCallRecord]:
        return self.collection.list_where(task_id=task_id)


class MemReportRepository:
    def __init__(self, collection: MemCollection[ReportArchive]) -> None:
        self.collection = collection

    def save(self, report: ReportArchive) -> ReportArchive:
        return self.collection.save(report)

    def get_by_task(self, task_id: str) -> ReportArchive | None:
        matches = self.collection.list_where(task_id=task_id)
        return matches[-1] if matches else None


class MemNotificationRepository:
    def __init__(
        self,
        channels: MemCollection[NotificationChannel],
        records: MemCollection[NotificationRecord],
    ) -> None:
        self.channels = channels
        self.records = records

    def save_channel(self, channel: NotificationChannel) -> NotificationChannel:
        return self.channels.save(channel)

    def get_channel(self, channel_id: str) -> NotificationChannel | None:
        return self.channels.get(channel_id)

    def list_channels(self, user_id: str) -> list[NotificationChannel]:
        return self.channels.list_where(user_id=user_id)

    def save_record(self, record: NotificationRecord) -> NotificationRecord:
        return self.records.save(record)

    def get_record(self, record_id: str) -> NotificationRecord | None:
        return self.records.get(record_id)

    def list_records(self, user_id: str) -> list[NotificationRecord]:
        channel_ids = {channel.channel_id for channel in self.list_channels(user_id)}
        return [record for record in self.records.list_all() if record.channel_id in channel_ids]

    def list_records_by_status(self, status: str) -> list[NotificationRecord]:
        return self.records.list_where(status=status)


class MemScheduledJobRepository:
    def __init__(self, collection: MemCollection[ScheduledJob]) -> None:
        self.collection = collection

    def save(self, job: ScheduledJob) -> ScheduledJob:
        return self.collection.save(job)

    def get(self, job_id: str) -> ScheduledJob | None:
        return self.collection.get(job_id)

    def list_by_user(self, user_id: str) -> list[ScheduledJob]:
        return self.collection.list_where(user_id=user_id)

    def list_enabled(self, user_id: str | None = None) -> list[ScheduledJob]:
        items = self.collection.list_where(enabled=True)
        if user_id:
            return [item for item in items if item.user_id == user_id]
        return items

    def delete(self, job_id: str) -> bool:
        return self.collection.delete(job_id)


class MemUnitOfWork:
    def __init__(self) -> None:
        self.users = MemUserRepository(MemCollection("user_id"))
        self.portfolios = MemPortfolioRepository(MemCollection("portfolio_id"))
        self.watch_items = MemWatchRepository(MemCollection("watch_id"))
        self.trade_journals = MemTradeJournalRepository(MemCollection("journal_id"))
        self.analysis_tasks = MemAnalysisTaskRepository(MemCollection("task_id"))
        self.agent_runs = MemAgentRunRepository(MemCollection("record_id"))
        self.tool_calls = MemToolCallRepository(MemCollection("call_id"))
        self.reports = MemReportRepository(MemCollection("report_id"))
        self.notifications = MemNotificationRepository(
            channels=MemCollection("channel_id"),
            records=MemCollection("record_id"),
        )
        self.scheduled_jobs = MemScheduledJobRepository(MemCollection("job_id"))

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None
