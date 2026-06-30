from __future__ import annotations

import unittest

from src.app.service.notification_service import NotificationService
from src.app.service.portfolio_service import PortfolioService
from src.app.service.schedule_service import ScheduleService
from src.app.task_executor import ScheduledTaskExecutor
from src.domain.entity import AnalysisTask, TaskStatus
from src.infra.repo.mem import MemUnitOfWork


class FakeTaskService:
    def __init__(self, uow: MemUnitOfWork) -> None:
        self.uow = uow
        self.calls: list[str] = []

    def create_task(self, user_id: str, portfolio_id: str) -> AnalysisTask:
        return self.uow.analysis_tasks.save(AnalysisTask(user_id=user_id, portfolio_id=portfolio_id))

    def run_report_check(self, task_id: str) -> AnalysisTask:
        self.calls.append("report")
        task = self.uow.analysis_tasks.get(task_id)
        task.status = TaskStatus.COMPLETED
        task.latest_observation = "report done"
        return self.uow.analysis_tasks.save(task)

    def run_announcement_check(self, task_id: str) -> AnalysisTask:
        self.calls.append("announcement")
        task = self.uow.analysis_tasks.get(task_id)
        task.status = TaskStatus.COMPLETED
        task.latest_observation = "announcement done"
        task.metadata["day7_result"] = {
            "risk_events": [{"severity": "high", "risk_label": "监管处罚"}],
        }
        return self.uow.analysis_tasks.save(task)

    def run_review_check(self, task_id: str) -> AnalysisTask:
        self.calls.append("review")
        task = self.uow.analysis_tasks.get(task_id)
        task.status = TaskStatus.COMPLETED
        task.latest_observation = "review done"
        return self.uow.analysis_tasks.save(task)


class DayTenSchedulerExecutorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.uow = MemUnitOfWork()
        self.schedule_service = ScheduleService(self.uow)
        self.notification_service = NotificationService(self.uow)
        self.task_service = FakeTaskService(self.uow)
        self.executor = ScheduledTaskExecutor(
            uow=self.uow,
            schedule_service=self.schedule_service,
            task_service=self.task_service,
            redis_runtime=None,
            notification_service=self.notification_service,
        )
        self.portfolio = PortfolioService(self.uow).create_portfolio(
            user_id="u_day10",
            name="Day10 组合",
            holdings_payload=[{"symbol": "300750", "shares": 100, "cost_price": 235, "name": "宁德时代"}],
        )

    def test_schedule_crud(self) -> None:
        job = self.schedule_service.create_job(
            "u_day10",
            {"job_type": "daily_portfolio_check", "target_id": self.portfolio.portfolio_id, "enabled": True},
        )
        self.assertEqual(self.schedule_service.get_job(job.job_id).job_type, "daily_portfolio_check")
        updated = self.schedule_service.update_job(job.job_id, {"enabled": False, "cron": "0 9 * * *"})
        self.assertFalse(updated.enabled)
        self.assertEqual(updated.status, "paused")
        self.assertEqual(updated.cron, "0 9 * * *")
        self.assertTrue(self.schedule_service.delete_job(job.job_id))

    def test_daily_portfolio_job_runs_report_and_records_notification(self) -> None:
        self.notification_service.create_channel(
            "u_day10",
            {
                "channel_type": "feishu",
                "channel_name": "risk",
                "webhook_url": "mock://day10",
                "event_types": ["report_ready"],
            },
        )
        job = self.schedule_service.create_job(
            "u_day10",
            {"job_type": "daily_portfolio_check", "target_id": self.portfolio.portfolio_id, "enabled": True},
        )
        result = self.executor.run_job(job.job_id)
        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(self.task_service.calls, ["report"])
        records = self.uow.notifications.list_records("u_day10")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].event_type, "report_ready")

    def test_running_task_causes_skip_reason(self) -> None:
        self.uow.analysis_tasks.save(AnalysisTask(user_id="u_day10", portfolio_id=self.portfolio.portfolio_id, status=TaskStatus.RUNNING))
        job = self.schedule_service.create_job(
            "u_day10",
            {"job_type": "announcement_radar", "target_id": self.portfolio.portfolio_id, "enabled": True},
        )
        result = self.executor.run_job(job.job_id)
        self.assertEqual(result["run_status"], "skipped")
        self.assertIn("上次任务未完成", result["reason"])
        self.assertIn("上次任务未完成", self.schedule_service.get_job(job.job_id).last_skip_reason)
        self.assertEqual(self.task_service.calls, [])

    def test_pending_manual_task_does_not_block_schedule(self) -> None:
        self.uow.analysis_tasks.save(AnalysisTask(user_id="u_day10", portfolio_id=self.portfolio.portfolio_id))
        job = self.schedule_service.create_job(
            "u_day10",
            {"job_type": "announcement_radar", "target_id": self.portfolio.portfolio_id, "enabled": True},
        )
        result = self.executor.run_job(job.job_id)
        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(self.task_service.calls, ["announcement"])

    def test_recover_unfinished_tasks_marks_running_failed(self) -> None:
        task = AnalysisTask(user_id="u_day10", portfolio_id=self.portfolio.portfolio_id, status=TaskStatus.RUNNING)
        self.uow.analysis_tasks.save(task)
        result = self.executor.recover_unfinished_tasks("u_day10")
        self.assertEqual(result["recovered_count"], 1)
        recovered = self.uow.analysis_tasks.get(task.task_id)
        self.assertEqual(recovered.status, TaskStatus.FAILED)
        self.assertIn("系统启动恢复", recovered.error_message)

    def test_enabled_job_scan_runs_multiple_types(self) -> None:
        self.schedule_service.create_job(
            "u_day10",
            {"job_type": "announcement_radar", "target_id": self.portfolio.portfolio_id, "enabled": True},
        )
        second = PortfolioService(self.uow).create_portfolio(
            user_id="u_day10",
            name="Day10 组合2",
            holdings_payload=[{"symbol": "000001", "shares": 1000, "cost_price": 10.8, "name": "平安银行"}],
        )
        self.schedule_service.create_job(
            "u_day10",
            {"job_type": "trade_review_reminder", "target_id": second.portfolio_id, "enabled": True},
        )
        result = self.executor.run_enabled_jobs("u_day10")
        self.assertEqual(result["run_count"], 2)
        self.assertEqual(self.task_service.calls, ["announcement", "review"])

    def test_announcement_radar_high_risk_event_notification(self) -> None:
        self.notification_service.create_channel(
            "u_day10",
            {
                "channel_type": "feishu",
                "channel_name": "high-risk",
                "webhook_url": "mock://high-risk",
                "event_types": ["high_risk_event"],
            },
        )
        job = self.schedule_service.create_job(
            "u_day10",
            {"job_type": "announcement_radar", "target_id": self.portfolio.portfolio_id, "enabled": True},
        )
        result = self.executor.run_job(job.job_id)
        self.assertEqual(result["run_status"], "completed")
        records = self.uow.notifications.list_records("u_day10")
        self.assertEqual(records[-1].event_type, "high_risk_event")
        self.assertEqual(records[-1].status, "sent")


if __name__ == "__main__":
    unittest.main()
