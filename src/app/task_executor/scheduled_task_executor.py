from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from src.app.service.notification_service import NotificationService
from src.app.service.redis_runtime_service import RedisRuntimeService
from src.app.service.schedule_service import ScheduleService
from src.app.service.task_service import TaskService
from src.domain.entity import AnalysisTask, ScheduledJob, TaskStatus
from src.domain.time import now_iso
from src.infra.repo.mem import MemUnitOfWork


logger = logging.getLogger(__name__)


UNFINISHED_STATUSES = {TaskStatus.RUNNING, TaskStatus.WAITING_RETRY}


class ScheduledTaskExecutor:
    def __init__(
        self,
        uow: MemUnitOfWork,
        schedule_service: ScheduleService,
        task_service: TaskService,
        redis_runtime: RedisRuntimeService | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self.uow = uow
        self.schedule_service = schedule_service
        self.task_service = task_service
        self.redis_runtime = redis_runtime
        self.notification_service = notification_service

    def run_enabled_jobs(self, user_id: str | None = None) -> dict[str, Any]:
        results = [self.run_job(job.job_id) for job in self.schedule_service.list_enabled_jobs(user_id=user_id)]
        return {"run_count": len(results), "results": results}

    def run_job(self, job_id: str) -> dict[str, Any]:
        job = self.schedule_service.get_job(job_id)
        if not job.enabled:
            reason = "任务未启用"
            self.schedule_service.mark_skip(job.job_id, reason)
            return self._result(job, "skipped", reason)

        lock_acquired = self._acquire_lock(job)
        if lock_acquired is False:
            reason = "上一个周期任务仍在运行，Redis 锁未释放"
            self.schedule_service.mark_skip(job.job_id, reason)
            return self._result(job, "skipped", reason)

        try:
            unfinished = self._find_unfinished_task(job)
            if unfinished is not None:
                reason = f"上次任务未完成：{unfinished.task_id} status={unfinished.status}"
                self.schedule_service.mark_skip(job.job_id, reason)
                return self._result(job, "skipped", reason, unfinished.task_id)

            task = self._create_task_for_job(job)
            completed = self._run_task_for_job(job, task)
            status = "completed" if completed.status == TaskStatus.COMPLETED else "failed"
            reason = completed.error_message or completed.latest_observation
            self.schedule_service.mark_run_result(job.job_id, "enabled" if job.enabled else "paused", "")
            self._record_notification(job, completed)
            return self._result(job, status, reason, completed.task_id)
        finally:
            self._release_lock(job, lock_acquired)

    def recover_unfinished_tasks(self, user_id: str | None = None) -> dict[str, Any]:
        recovered = []
        tasks = self._list_tasks(user_id)
        for task in tasks:
            if task.status in {TaskStatus.RUNNING, TaskStatus.WAITING_RETRY}:
                task.status = TaskStatus.FAILED
                task.error_message = "系统启动恢复：任务处于未完成状态，已标记失败，等待人工重新触发。"
                task.latest_observation = "任务状态恢复完成。"
                task.updated_at = now_iso()
                self.uow.analysis_tasks.save(task)
                recovered.append(task.task_id)
        return {"recovered_count": len(recovered), "task_ids": recovered}

    def _create_task_for_job(self, job: ScheduledJob) -> AnalysisTask:
        portfolio = self.uow.portfolios.get(job.target_id)
        if portfolio is None:
            raise ValueError("定时任务目标组合不存在")
        return self.task_service.create_task(job.user_id, portfolio.portfolio_id)

    def _run_task_for_job(self, job: ScheduledJob, task: AnalysisTask) -> AnalysisTask:
        if job.job_type in {"daily_portfolio_check", "weekly_portfolio_report"}:
            return self.task_service.run_report_check(task.task_id)
        if job.job_type == "announcement_radar":
            return self.task_service.run_announcement_check(task.task_id)
        if job.job_type == "trade_review_reminder":
            return self.task_service.run_review_check(task.task_id)
        reason = f"任务类型暂未实现执行器：{job.job_type}"
        self.schedule_service.mark_skip(job.job_id, reason)
        task.status = TaskStatus.CANCELLED
        task.error_message = reason
        task.updated_at = now_iso()
        return self.uow.analysis_tasks.save(task)

    def _find_unfinished_task(self, job: ScheduledJob) -> AnalysisTask | None:
        for task in self._list_tasks(job.user_id):
            if task.portfolio_id == job.target_id and task.status in UNFINISHED_STATUSES:
                return task
        return None

    def _list_tasks(self, user_id: str | None = None) -> list[AnalysisTask]:
        if user_id:
            return self.uow.analysis_tasks.list_by_user(user_id)
        return self.uow.analysis_tasks.list_all()

    def _acquire_lock(self, job: ScheduledJob) -> bool | None:
        if self.redis_runtime is None:
            return None
        try:
            return self.redis_runtime.acquire_schedule_lock(job.job_type, job.target_id or job.job_id, ttl_seconds=3600)
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to acquire schedule lock, running without redis lock: job_id=%s error=%s", job.job_id, exc)
            return None

    def _release_lock(self, job: ScheduledJob, lock_acquired: bool | None) -> None:
        if not lock_acquired or self.redis_runtime is None:
            return
        try:
            self.redis_runtime.release_schedule_lock(job.job_type, job.target_id or job.job_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to release schedule lock: job_id=%s error=%s", job.job_id, exc)

    def _record_notification(self, job: ScheduledJob, task: AnalysisTask) -> None:
        if self.notification_service is None:
            return
        if task.status == TaskStatus.COMPLETED:
            event_type = self._completed_event_type(job, task)
            title = "高风险事件提醒" if event_type == "high_risk_event" else "风险扫描任务完成"
        else:
            event_type = "task_failed"
            title = "风险扫描任务失败"
        self.notification_service.dispatch_event(
            user_id=job.user_id,
            event_type=event_type,
            title=title,
            content=f"job_type={job.job_type}, task_id={task.task_id}, status={task.status}",
        )

    def _completed_event_type(self, job: ScheduledJob, task: AnalysisTask) -> str:
        if job.job_type in {"daily_portfolio_check", "weekly_portfolio_report"}:
            return "report_ready"
        if job.job_type == "announcement_radar":
            events = task.metadata.get("day7_result", {}).get("risk_events", [])
            if any(event.get("severity") in {"high", "critical"} for event in events):
                return "high_risk_event"
        return job.job_type

    def _result(self, job: ScheduledJob, status: str, reason: str = "", task_id: str = "") -> dict[str, Any]:
        data = asdict(job)
        data.update({"run_status": status, "reason": reason, "task_id": task_id})
        return data
