from __future__ import annotations

from typing import Any

from src.domain.entity import ScheduledJob
from src.domain.time import now_iso
from src.infra.repo.mem import MemUnitOfWork


VALID_JOB_TYPES = {
    "daily_portfolio_check",
    "weekly_portfolio_report",
    "announcement_radar",
    "price_alert_scan",
    "trade_review_reminder",
}


class ScheduleService:
    def __init__(self, uow: MemUnitOfWork) -> None:
        self.uow = uow

    def create_job(self, user_id: str, payload: dict[str, Any]) -> ScheduledJob:
        job_type = payload["job_type"]
        if job_type not in VALID_JOB_TYPES:
            raise ValueError("不支持的定时任务类型")
        enabled = bool(payload.get("enabled", False))
        job = ScheduledJob(
            user_id=user_id,
            job_type=job_type,
            target_id=payload.get("target_id", ""),
            enabled=enabled,
            cron=payload.get("cron", ""),
            status="enabled" if enabled else "paused",
        )
        return self.uow.scheduled_jobs.save(job)

    def get_job(self, job_id: str) -> ScheduledJob:
        job = self.uow.scheduled_jobs.get(job_id)
        if job is None:
            raise ValueError("定时任务不存在")
        return job

    def list_jobs(self, user_id: str) -> list[ScheduledJob]:
        return self.uow.scheduled_jobs.list_by_user(user_id)

    def list_enabled_jobs(self, user_id: str | None = None) -> list[ScheduledJob]:
        return self.uow.scheduled_jobs.list_enabled(user_id=user_id)

    def update_job(self, job_id: str, payload: dict[str, Any]) -> ScheduledJob:
        job = self.get_job(job_id)
        if "job_type" in payload and payload["job_type"] != job.job_type:
            if payload["job_type"] not in VALID_JOB_TYPES:
                raise ValueError("不支持的定时任务类型")
            job.job_type = payload["job_type"]
        if "target_id" in payload:
            job.target_id = str(payload["target_id"])
        if "cron" in payload:
            job.cron = str(payload["cron"])
        if "enabled" in payload:
            job.enabled = bool(payload["enabled"])
            job.status = "enabled" if job.enabled else "paused"
        job.updated_at = now_iso()
        return self.uow.scheduled_jobs.save(job)

    def delete_job(self, job_id: str) -> bool:
        deleted = self.uow.scheduled_jobs.delete(job_id)
        if not deleted:
            raise ValueError("定时任务不存在")
        return True

    def mark_skip(self, job_id: str, reason: str) -> ScheduledJob:
        job = self.get_job(job_id)
        job.status = "skipped"
        job.last_skip_reason = reason[:500]
        job.updated_at = now_iso()
        return self.uow.scheduled_jobs.save(job)

    def mark_run_result(self, job_id: str, status: str, reason: str = "") -> ScheduledJob:
        job = self.get_job(job_id)
        job.status = status
        job.last_skip_reason = reason[:500]
        job.updated_at = now_iso()
        return self.uow.scheduled_jobs.save(job)
