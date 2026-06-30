from __future__ import annotations

from dataclasses import dataclass

from config.settings import AppSettings, get_settings
from src.app.service.agent_runtime_service import AgentRuntimeService
from src.app.service.announcement_rag_service import AnnouncementRAGService
from src.app.service.evaluation import EvaluationService, OfficialBenchmarkService
from src.app.service.health_service import HealthService
from src.app.service.notification_service import NotificationService
from src.app.service.redis_runtime_service import RedisRuntimeService
from src.app.service.report_archive_service import ReportArchiveService
from src.app.service.report_service import ReportService
from src.app.service.portfolio_service import PortfolioService
from src.app.service.schedule_service import ScheduleService
from src.app.service.task_service import TaskService
from src.app.service.tool_service import ToolService
from src.app.service.trade_journal_service import TradeJournalService
from src.app.service.trade_review_service import TradeReviewService
from src.app.service.vector_memory_service import VectorMemoryService
from src.app.service.watch_service import WatchService
from src.app.task_executor import ScheduledTaskExecutor
from src.infra.adapter.mcp import MCPToolRegistry
from src.infra.adapter.mcp.announcement_toolkit import register_announcement_tools
from src.infra.adapter.mcp.financial_toolkit import register_financial_tools
from src.infra.adapter.mcp.report_toolkit import register_report_tools
from src.infra.adapter.mcp.review_toolkit import register_review_tools
from src.infra.adapter.mcp.search_toolkit import register_search_tools
from src.infra.external.ollama_client import OllamaClient
from src.infra.external.feishu_client import FeishuBotClient, FeishuCLIClient
from src.infra.external.market_data_gateway import MarketDataGateway
from src.infra.external.search_gateway import AdvancedSearchGateway
from src.infra.repo.mem import MemUnitOfWork
from src.infra.repo.mongo import MongoUnitOfWork
from src.infra.repo.mongo import MongoClientProvider
from src.infra.repo.redis import RedisClientProvider
from src.infra.repo.vector import VectorStoreProvider


@dataclass(slots=True)
class AppContainer:
    settings: AppSettings
    uow: MemUnitOfWork | MongoUnitOfWork
    mongo: MongoClientProvider
    redis: RedisClientProvider
    redis_runtime_service: RedisRuntimeService
    vector: VectorStoreProvider
    vector_memory_service: VectorMemoryService
    announcement_rag_service: AnnouncementRAGService
    ollama: OllamaClient
    tool_registry: MCPToolRegistry
    market_data_gateway: MarketDataGateway
    search_gateway: AdvancedSearchGateway
    feishu_bot: FeishuBotClient
    feishu_cli: FeishuCLIClient
    health_service: HealthService
    portfolio_service: PortfolioService
    watch_service: WatchService
    trade_journal_service: TradeJournalService
    trade_review_service: TradeReviewService
    report_service: ReportService
    report_archive_service: ReportArchiveService
    task_service: TaskService
    scheduled_task_executor: ScheduledTaskExecutor
    tool_service: ToolService
    agent_runtime_service: AgentRuntimeService
    notification_service: NotificationService
    schedule_service: ScheduleService
    evaluation_service: EvaluationService
    official_benchmark_service: OfficialBenchmarkService


def create_container(settings: AppSettings | None = None) -> AppContainer:
    settings = settings or get_settings()
    mongo = MongoClientProvider(settings.mongo)
    uow = MemUnitOfWork() if settings.use_memory_fallback else MongoUnitOfWork(settings.mongo)
    redis = RedisClientProvider(settings.redis)
    redis_runtime = RedisRuntimeService(settings.redis, redis)
    vector = VectorStoreProvider(settings.vector)
    ollama = OllamaClient(settings.model)
    vector_memory = VectorMemoryService(settings.vector, vector, ollama.embed)
    configured_market_data = MarketDataGateway(settings=settings.market_data)
    announcement_rag = AnnouncementRAGService(configured_market_data, vector_memory)
    trade_review = TradeReviewService(uow, vector_memory)
    report_service = ReportService(uow, ollama)
    registry = MCPToolRegistry(uow)
    market_data_gateway = announcement_rag.market_data
    search_gateway = AdvancedSearchGateway(settings.search)
    feishu_bot = FeishuBotClient()
    feishu_cli = FeishuCLIClient()
    register_financial_tools(registry, market_data_gateway)
    register_search_tools(registry, search_gateway)
    register_announcement_tools(registry, announcement_rag)
    register_review_tools(registry, trade_review)
    notification_service = NotificationService(uow, feishu_bot, feishu_cli)
    register_report_tools(registry, report_service)
    task_service = TaskService(uow, registry, redis_runtime, notification_service)
    schedule_service = ScheduleService(uow)
    scheduled_task_executor = ScheduledTaskExecutor(
        uow=uow,
        schedule_service=schedule_service,
        task_service=task_service,
        redis_runtime=redis_runtime,
        notification_service=notification_service,
    )
    return AppContainer(
        settings=settings,
        uow=uow,
        mongo=mongo,
        redis=redis,
        redis_runtime_service=redis_runtime,
        vector=vector,
        vector_memory_service=vector_memory,
        announcement_rag_service=announcement_rag,
        ollama=ollama,
        tool_registry=registry,
        market_data_gateway=market_data_gateway,
        search_gateway=search_gateway,
        feishu_bot=feishu_bot,
        feishu_cli=feishu_cli,
        health_service=HealthService(settings, mongo, redis, vector, ollama, search_gateway, market_data_gateway),
        portfolio_service=PortfolioService(uow),
        watch_service=WatchService(uow),
        trade_journal_service=TradeJournalService(uow),
        trade_review_service=trade_review,
        report_service=report_service,
        report_archive_service=ReportArchiveService(uow),
        task_service=task_service,
        scheduled_task_executor=scheduled_task_executor,
        tool_service=ToolService(registry),
        agent_runtime_service=AgentRuntimeService(settings.model, ollama, registry, uow),
        notification_service=notification_service,
        schedule_service=schedule_service,
        evaluation_service=EvaluationService(
            uow=uow,
            registry=registry,
            task_service=task_service,
            report_archive_service=ReportArchiveService(uow),
            report_service=report_service,
            notification_service=notification_service,
        ),
        official_benchmark_service=OfficialBenchmarkService(),
    )
