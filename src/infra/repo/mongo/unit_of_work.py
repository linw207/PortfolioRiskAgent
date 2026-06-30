from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar

from config.settings import MongoSettings
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
from src.infra.repo.encoder_decoder import encode
from src.infra.repo.mongo.client import MongoClientProvider
from src.infra.repo.mongo.decoder import (
    decode_agent_run,
    decode_analysis_task,
    decode_notification_channel,
    decode_notification_record,
    decode_portfolio,
    decode_report,
    decode_scheduled_job,
    decode_tool_call,
    decode_trade_journal,
    decode_user,
    decode_watch_item,
)


T = TypeVar("T")


class MongoCollectionRepository(Generic[T]):
    def __init__(self, collection: Any, id_field: str, decoder: Callable[[dict[str, Any]], T]) -> None:
        self.collection = collection
        self.id_field = id_field
        self.decoder = decoder

    def save(self, item: T) -> T:
        document = encode(item)
        self.collection.replace_one({self.id_field: document[self.id_field]}, document, upsert=True)
        return item

    def get(self, item_id: str) -> T | None:
        document = self.collection.find_one({self.id_field: item_id})
        return self.decoder(document) if document else None

    def list_all(self) -> list[T]:
        return [self.decoder(document) for document in self.collection.find({})]

    def list_where(self, **conditions: Any) -> list[T]:
        return [self.decoder(document) for document in self.collection.find(encode(conditions))]

    def delete(self, item_id: str) -> bool:
        return self.collection.delete_one({self.id_field: item_id}).deleted_count > 0


class MongoUserRepository:
    def __init__(self, repo: MongoCollectionRepository[User]) -> None:
        self.repo = repo

    def save(self, user: User) -> User:
        return self.repo.save(user)

    def get(self, user_id: str) -> User | None:
        return self.repo.get(user_id)


class MongoPortfolioRepository:
    def __init__(self, repo: MongoCollectionRepository[Portfolio]) -> None:
        self.repo = repo

    def save(self, portfolio: Portfolio) -> Portfolio:
        return self.repo.save(portfolio)

    def get(self, portfolio_id: str) -> Portfolio | None:
        return self.repo.get(portfolio_id)

    def list_by_user(self, user_id: str) -> list[Portfolio]:
        return self.repo.list_where(user_id=user_id)


class MongoWatchRepository:
    def __init__(self, repo: MongoCollectionRepository[WatchItem]) -> None:
        self.repo = repo

    def save(self, item: WatchItem) -> WatchItem:
        return self.repo.save(item)

    def list_by_user(self, user_id: str) -> list[WatchItem]:
        return self.repo.list_where(user_id=user_id)

    def delete(self, watch_id: str) -> bool:
        return self.repo.delete(watch_id)


class MongoTradeJournalRepository:
    def __init__(self, repo: MongoCollectionRepository[TradeJournal]) -> None:
        self.repo = repo

    def save(self, journal: TradeJournal) -> TradeJournal:
        return self.repo.save(journal)

    def list_by_user(self, user_id: str, symbol: str | None = None) -> list[TradeJournal]:
        query = {"user_id": user_id}
        if symbol:
            query["symbol"] = symbol
        return self.repo.list_where(**query)


class MongoAnalysisTaskRepository:
    def __init__(self, repo: MongoCollectionRepository[AnalysisTask]) -> None:
        self.repo = repo

    def save(self, task: AnalysisTask) -> AnalysisTask:
        return self.repo.save(task)

    def get(self, task_id: str) -> AnalysisTask | None:
        return self.repo.get(task_id)

    def list_by_user(self, user_id: str) -> list[AnalysisTask]:
        return self.repo.list_where(user_id=user_id)

    def list_all(self) -> list[AnalysisTask]:
        return self.repo.list_all()


class MongoAgentRunRepository:
    def __init__(self, repo: MongoCollectionRepository[AgentRunRecord]) -> None:
        self.repo = repo

    def save(self, record: AgentRunRecord) -> AgentRunRecord:
        return self.repo.save(record)

    def list_by_task(self, task_id: str) -> list[AgentRunRecord]:
        return self.repo.list_where(task_id=task_id)


class MongoToolCallRepository:
    def __init__(self, repo: MongoCollectionRepository[ToolCallRecord]) -> None:
        self.repo = repo

    def save(self, record: ToolCallRecord) -> ToolCallRecord:
        return self.repo.save(record)

    def list_by_task(self, task_id: str) -> list[ToolCallRecord]:
        return self.repo.list_where(task_id=task_id)


class MongoReportRepository:
    def __init__(self, repo: MongoCollectionRepository[ReportArchive]) -> None:
        self.repo = repo

    def save(self, report: ReportArchive) -> ReportArchive:
        return self.repo.save(report)

    def get_by_task(self, task_id: str) -> ReportArchive | None:
        matches = self.repo.list_where(task_id=task_id)
        return matches[-1] if matches else None


class MongoNotificationRepository:
    def __init__(
        self,
        channels: MongoCollectionRepository[NotificationChannel],
        records: MongoCollectionRepository[NotificationRecord],
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


class MongoScheduledJobRepository:
    def __init__(self, repo: MongoCollectionRepository[ScheduledJob]) -> None:
        self.repo = repo

    def save(self, job: ScheduledJob) -> ScheduledJob:
        return self.repo.save(job)

    def get(self, job_id: str) -> ScheduledJob | None:
        return self.repo.get(job_id)

    def list_by_user(self, user_id: str) -> list[ScheduledJob]:
        return self.repo.list_where(user_id=user_id)

    def list_enabled(self, user_id: str | None = None) -> list[ScheduledJob]:
        query: dict[str, Any] = {"enabled": True}
        if user_id:
            query["user_id"] = user_id
        return self.repo.list_where(**query)

    def delete(self, job_id: str) -> bool:
        return self.repo.delete(job_id)


class MongoUnitOfWork:
    def __init__(self, settings: MongoSettings) -> None:
        self.provider = MongoClientProvider(settings)
        db = self.provider.sync_database()
        self.users = MongoUserRepository(MongoCollectionRepository(db.users, "user_id", decode_user))
        self.portfolios = MongoPortfolioRepository(MongoCollectionRepository(db.portfolios, "portfolio_id", decode_portfolio))
        self.watch_items = MongoWatchRepository(MongoCollectionRepository(db.watch_items, "watch_id", decode_watch_item))
        self.trade_journals = MongoTradeJournalRepository(
            MongoCollectionRepository(db.trade_journals, "journal_id", decode_trade_journal)
        )
        self.analysis_tasks = MongoAnalysisTaskRepository(
            MongoCollectionRepository(db.analysis_tasks, "task_id", decode_analysis_task)
        )
        self.agent_runs = MongoAgentRunRepository(
            MongoCollectionRepository(db.agent_run_records, "record_id", decode_agent_run)
        )
        self.tool_calls = MongoToolCallRepository(
            MongoCollectionRepository(db.tool_call_records, "call_id", decode_tool_call)
        )
        self.reports = MongoReportRepository(MongoCollectionRepository(db.report_archives, "report_id", decode_report))
        self.notifications = MongoNotificationRepository(
            channels=MongoCollectionRepository(db.notification_channels, "channel_id", decode_notification_channel),
            records=MongoCollectionRepository(db.notification_records, "record_id", decode_notification_record),
        )
        self.scheduled_jobs = MongoScheduledJobRepository(
            MongoCollectionRepository(db.scheduled_jobs, "job_id", decode_scheduled_job)
        )

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None
