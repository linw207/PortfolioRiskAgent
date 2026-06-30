from __future__ import annotations

import logging

from src.app.service.agents import AnnouncementAgent, FinanceAgent, OrchestratorAgent, ReportAgent, ReviewAgent
from src.app.service.notification_service import NotificationService
from src.app.service.redis_runtime_service import RedisRuntimeService
from src.domain.entity import AnalysisTask, TaskStatus
from src.domain.time import now_iso
from src.infra.repo.mem import MemUnitOfWork
from src.infra.adapter.mcp import MCPToolRegistry


logger = logging.getLogger(__name__)


class TaskService:
    def __init__(
        self,
        uow: MemUnitOfWork,
        registry: MCPToolRegistry | None = None,
        redis_runtime: RedisRuntimeService | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self.uow = uow
        self.registry = registry
        self.redis_runtime = redis_runtime
        self.notification_service = notification_service

    def create_task(self, user_id: str, portfolio_id: str) -> AnalysisTask:
        portfolio = self.uow.portfolios.get(portfolio_id)
        if portfolio is None:
            raise ValueError("持仓组合不存在")
        if not portfolio.holdings:
            raise ValueError("持仓数量必须大于 0")
        task = AnalysisTask(user_id=user_id, portfolio_id=portfolio_id, total_steps=0)
        saved = self.uow.analysis_tasks.save(task)
        self._sync_redis_task_status(saved)
        self._enqueue_redis_analysis_task(saved.task_id)
        return saved

    def get_task(self, task_id: str) -> AnalysisTask:
        task = self.uow.analysis_tasks.get(task_id)
        if task is None:
            raise ValueError("分析任务不存在")
        return task

    def list_tasks(self, user_id: str) -> list[AnalysisTask]:
        return self.uow.analysis_tasks.list_by_user(user_id)

    def run_finance_check(self, task_id: str) -> AnalysisTask:
        if self.registry is None:
            raise RuntimeError("MCP tool registry is not configured")
        task = self.get_task(task_id)
        portfolio = self.uow.portfolios.get(task.portfolio_id)
        if portfolio is None:
            raise ValueError("持仓组合不存在")

        task.status = TaskStatus.RUNNING
        task.current_agent = "OrchestratorAgent"
        task.current_action = "run_finance_agent"
        task.total_steps = 2
        task.updated_at = now_iso()
        self.uow.analysis_tasks.save(task)
        self._sync_redis_task_status(task)

        try:
            finance_agent = FinanceAgent(self.registry, self.uow)
            orchestrator = OrchestratorAgent(self.registry, self.uow)
            orchestrator.register_professional_agents(finance_agent.run)
            result = orchestrator.run(task.task_id, portfolio)
            task.status = TaskStatus.COMPLETED
            task.completed_steps = 2
            task.current_agent = "OrchestratorAgent"
            task.current_action = "completed"
            task.latest_observation = "Day6 金融分析任务完成。"
            task.metadata["day6_result"] = result
            task.updated_at = now_iso()
            saved = self.uow.analysis_tasks.save(task)
            self._sync_redis_task_status(saved)
            return saved
        except Exception as exc:  # noqa: BLE001
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)
            task.latest_observation = "Day6 金融分析任务失败。"
            task.updated_at = now_iso()
            saved = self.uow.analysis_tasks.save(task)
            self._sync_redis_task_status(saved)
            return saved

    def run_announcement_check(self, task_id: str) -> AnalysisTask:
        if self.registry is None:
            raise RuntimeError("MCP tool registry is not configured")
        task = self.get_task(task_id)
        portfolio = self.uow.portfolios.get(task.portfolio_id)
        if portfolio is None:
            raise ValueError("持仓组合不存在")

        task.status = TaskStatus.RUNNING
        task.current_agent = "AnnouncementAgent"
        task.current_action = "announcement_rag"
        task.total_steps = max(task.total_steps, 1)
        task.updated_at = now_iso()
        self.uow.analysis_tasks.save(task)
        self._sync_redis_task_status(task)

        try:
            announcement_agent = AnnouncementAgent(self.registry, self.uow)
            result = announcement_agent.run(task.task_id, portfolio)
            task.status = TaskStatus.COMPLETED
            task.completed_steps = max(task.completed_steps, 1)
            task.current_agent = "AnnouncementAgent"
            task.current_action = "completed"
            task.latest_observation = result.get("summary", "Day7 公告分析任务完成。")
            task.metadata["day7_result"] = result
            task.updated_at = now_iso()
            saved = self.uow.analysis_tasks.save(task)
            self._sync_redis_task_status(saved)
            return saved
        except Exception as exc:  # noqa: BLE001
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)
            task.latest_observation = "Day7 公告分析任务失败。"
            task.updated_at = now_iso()
            saved = self.uow.analysis_tasks.save(task)
            self._sync_redis_task_status(saved)
            return saved

    def run_review_check(self, task_id: str) -> AnalysisTask:
        if self.registry is None:
            raise RuntimeError("MCP tool registry is not configured")
        task = self.get_task(task_id)
        portfolio = self.uow.portfolios.get(task.portfolio_id)
        if portfolio is None:
            raise ValueError("持仓组合不存在")

        task.status = TaskStatus.RUNNING
        task.current_agent = "ReviewAgent"
        task.current_action = "trade_review_reflection"
        task.total_steps = max(task.total_steps, 1)
        task.updated_at = now_iso()
        self.uow.analysis_tasks.save(task)
        self._sync_redis_task_status(task)

        try:
            review_agent = ReviewAgent(self.registry, self.uow)
            result = review_agent.run(task.task_id, portfolio)
            task.status = TaskStatus.COMPLETED
            task.completed_steps = max(task.completed_steps, 1)
            task.current_agent = "ReviewAgent"
            task.current_action = "completed"
            task.latest_observation = result.get("summary", "Day8 交易复盘任务完成。")
            task.metadata["day8_result"] = result
            task.updated_at = now_iso()
            saved = self.uow.analysis_tasks.save(task)
            self._sync_redis_task_status(saved)
            return saved
        except Exception as exc:  # noqa: BLE001
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)
            task.latest_observation = "Day8 交易复盘任务失败。"
            task.updated_at = now_iso()
            saved = self.uow.analysis_tasks.save(task)
            self._sync_redis_task_status(saved)
            return saved

    def run_report_check(self, task_id: str, notify: bool = False) -> AnalysisTask:
        if self.registry is None:
            raise RuntimeError("MCP tool registry is not configured")
        task = self.get_task(task_id)
        portfolio = self.uow.portfolios.get(task.portfolio_id)
        if portfolio is None:
            raise ValueError("持仓组合不存在")

        task.status = TaskStatus.RUNNING
        task.current_agent = "ReportAgent"
        task.current_action = "render_guardrail_archive_report"
        task.total_steps = max(task.total_steps, 1)
        task.updated_at = now_iso()
        self.uow.analysis_tasks.save(task)
        self._sync_redis_task_status(task)

        try:
            report_agent = ReportAgent(self.registry, self.uow)
            result = report_agent.run(task, portfolio)
            task.status = TaskStatus.COMPLETED
            task.completed_steps = max(task.completed_steps, 1)
            task.current_agent = "ReportAgent"
            task.current_action = "completed"
            task.latest_observation = result.get("summary", "Day9 报告任务完成。")
            task.metadata["day9_result"] = result
            task.updated_at = now_iso()
            saved = self.uow.analysis_tasks.save(task)
            self._sync_redis_task_status(saved)
            if notify:
                self._dispatch_report_notification(saved)
            return saved
        except Exception as exc:  # noqa: BLE001
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)
            task.latest_observation = "Day9 报告任务失败。"
            task.updated_at = now_iso()
            saved = self.uow.analysis_tasks.save(task)
            self._sync_redis_task_status(saved)
            if notify:
                self._dispatch_report_notification(saved)
            return saved

    def _sync_redis_task_status(self, task: AnalysisTask) -> None:
        if self.redis_runtime is None:
            return
        try:
            self.redis_runtime.save_task_status(task)
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to sync task status to redis: task_id=%s error=%s", task.task_id, exc)

    def _enqueue_redis_analysis_task(self, task_id: str) -> None:
        if self.redis_runtime is None:
            return
        try:
            self.redis_runtime.enqueue_analysis_task(task_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to enqueue analysis task to redis: task_id=%s error=%s", task_id, exc)

    def _dispatch_report_notification(self, task: AnalysisTask) -> None:
        if self.notification_service is None:
            return
        if task.status == TaskStatus.COMPLETED:
            event_type = "report_ready"
            title = "风险扫描任务完成"
        else:
            event_type = "task_failed"
            title = "风险扫描任务失败"
        try:
            self.notification_service.dispatch_event(
                user_id=task.user_id,
                event_type=event_type,
                title=title,
                content=f"manual_report, task_id={task.task_id}, status={task.status}, observation={task.latest_observation or task.error_message}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to dispatch task notification: task_id=%s error=%s", task.task_id, exc)
