from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.domain.entity import AnalysisTask, TaskStatus
from src.factory import create_container


def main() -> None:
    container = create_container()
    portfolio = container.portfolio_service.create_portfolio(
        user_id="day10_smoke_user",
        name="Day10 Scheduler Smoke",
        holdings_payload=[{"symbol": "300750", "shares": 100, "cost_price": 235, "name": "宁德时代"}],
    )
    container.trade_journal_service.add_journal(
        "day10_smoke_user",
        {
            "symbol": "300750",
            "action": "buy",
            "trade_date": "2026-05-01",
            "price": 235,
            "shares": 100,
            "reason": "看好成长和业绩增长，长期持有。",
        },
    )
    container.notification_service.create_channel(
        "day10_smoke_user",
        {
            "channel_type": "feishu",
            "channel_name": "day10-smoke",
            "webhook_url": "mock://day10",
            "event_types": ["report_ready", "task_failed"],
        },
    )
    job = container.schedule_service.create_job(
        "day10_smoke_user",
        {"job_type": "daily_portfolio_check", "target_id": portfolio.portfolio_id, "enabled": True, "cron": "0 9 * * *"},
    )
    run = container.scheduled_task_executor.run_job(job.job_id)
    report = container.report_archive_service.get_by_task(run["task_id"])
    notifications = container.uow.notifications.list_records("day10_smoke_user")
    print("run_status=", run["run_status"])
    print("task_id=", run["task_id"])
    print("report_id=", report.report_id)
    print("notification_records=", len(notifications))

    blocked_portfolio = container.portfolio_service.create_portfolio(
        user_id="day10_smoke_user",
        name="Day10 Skip Smoke",
        holdings_payload=[{"symbol": "000001", "shares": 1000, "cost_price": 10.8, "name": "平安银行"}],
    )
    pending = AnalysisTask(user_id="day10_smoke_user", portfolio_id=blocked_portfolio.portfolio_id)
    container.uow.analysis_tasks.save(pending)
    skip_job = container.schedule_service.create_job(
        "day10_smoke_user",
        {"job_type": "announcement_radar", "target_id": blocked_portfolio.portfolio_id, "enabled": True},
    )
    skipped = container.scheduled_task_executor.run_job(skip_job.job_id)
    print("skip_status=", skipped["run_status"])
    print("skip_reason_has_unfinished=", "上次任务未完成" in skipped["reason"])

    running = AnalysisTask(user_id="day10_smoke_user", portfolio_id=blocked_portfolio.portfolio_id, status=TaskStatus.RUNNING)
    container.uow.analysis_tasks.save(running)
    recovered = container.scheduled_task_executor.recover_unfinished_tasks("day10_smoke_user")
    print("recovered_count=", recovered["recovered_count"])


if __name__ == "__main__":
    main()
