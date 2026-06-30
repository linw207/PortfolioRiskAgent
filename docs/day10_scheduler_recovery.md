# Day10 Scheduler, Active Risk Scan, and Recovery

Day10 implements active risk scan execution, schedule CRUD, skip reasons, and recovery for unfinished tasks.

## Implemented Scope

- Schedule CRUD:
  - `POST /schedules`
  - `GET /schedules`
  - `GET /schedules/{job_id}`
  - `PATCH /schedules/{job_id}`
  - `DELETE /schedules/{job_id}`
- Manual scheduled execution:
  - `POST /schedules/{job_id}/run`
  - `POST /schedules/run-enabled`
- Recovery:
  - `POST /schedules/recover`
- Task executor:
  - `ScheduledTaskExecutor`
  - Uses Redis schedule locks when available.
  - Runs without Redis lock in local fallback if Redis is unavailable.
- Supported job types:
  - `daily_portfolio_check` -> report task, which runs finance, announcement, review, report if needed.
  - `weekly_portfolio_report` -> report task.
  - `announcement_radar` -> announcement check.
  - `trade_review_reminder` -> review check.
- Skip reason:
  - If a previous task for the same target portfolio is still pending/running/waiting_retry, the new scheduled run is skipped and `last_skip_reason` is saved.
- Recovery:
  - Running or waiting_retry tasks can be marked failed on startup/manual recovery with a clear recovery message.
  - If `user_id` is omitted, recovery scans all analysis tasks through the repository.
- Notification preparation:
  - Completed/failed scheduled runs create `NotificationRecord` entries for Day11 delivery.

## Verification

Commands run:

```bash
python3 -B -m compileall -q src config log scripts tests
python3 -B -m unittest discover -s tests
python3 -B scripts/day10_scheduler_smoke.py
```

Smoke result:

- Scheduled daily portfolio check completed.
- Report archived successfully.
- Notification record count: 1.
- Announcement radar skipped when previous pending task existed.
- Recovery marked one running task as failed.

## Known Limits

- Cron parsing is not implemented yet. Day10 exposes manual `run-enabled`; an external cron, APScheduler, or worker process can call it.
- Real Feishu/WeCom sending is Day11. Day10 only creates notification records.
