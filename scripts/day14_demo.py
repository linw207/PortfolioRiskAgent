from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.factory import create_container


USER_ID = "user_demo"


def main() -> None:
    container = create_container()

    portfolio = container.portfolio_service.create_portfolio(
        user_id=USER_ID,
        name="Day14 演示组合",
        holdings_payload=[
            {"symbol": "300750.SZ", "name": "宁德时代", "shares": 100, "cost_price": 180.0},
            {"symbol": "600519.SH", "name": "贵州茅台", "shares": 10, "cost_price": 1600.0},
            {"symbol": "000001.SZ", "name": "平安银行", "shares": 1000, "cost_price": 10.5},
        ],
    )

    container.trade_journal_service.add_journal(
        USER_ID,
        {
            "symbol": "300750.SZ",
            "action": "buy",
            "trade_date": "2026-06-20",
            "price": 180.0,
            "shares": 100,
            "reason": "新能源长期景气，但短期公告和估值波动需要持续复核。",
        },
    )

    channel = container.notification_service.create_channel(
        USER_ID,
        {
            "channel_type": "feishu",
            "channel_name": "Day14 mock 飞书",
            "webhook_url": "mock://day14-demo",
            "event_types": ["report_ready", "task_failed", "high_risk_event"],
        },
    )

    schedule = container.schedule_service.create_job(
        USER_ID,
        {
            "job_name": "Day14 每日持仓体检",
            "job_type": "daily_portfolio_check",
            "portfolio_id": portfolio.portfolio_id,
            "cron": "0 9 * * 1-5",
            "enabled": True,
            "metadata": {"source": "day14_demo"},
        },
    )

    task = container.task_service.create_task(USER_ID, portfolio.portfolio_id)
    task.metadata.update(_stable_sections())
    container.uow.analysis_tasks.save(task)
    finished = container.task_service.run_report_check(task.task_id, notify=True)
    report = container.report_archive_service.get_by_task(task.task_id)
    records = container.notification_service.list_records(USER_ID)

    output = {
        "user_id": USER_ID,
        "portfolio_id": portfolio.portfolio_id,
        "task_id": finished.task_id,
        "task_status": finished.status,
        "report_id": report.report_id if report else "",
        "notification_channel_id": channel.channel_id,
        "notification_records": [
            {"record_id": item.record_id, "event_type": item.event_type, "status": item.status}
            for item in records
        ],
        "schedule_id": schedule.job_id,
        "demo_url": "http://127.0.0.1:8000/app",
        "recommended_api_checks": [
            f"curl 'http://127.0.0.1:8000/portfolios?user_id={USER_ID}'",
            f"curl 'http://127.0.0.1:8000/tasks/{finished.task_id}/agent-runs'",
            f"curl 'http://127.0.0.1:8000/reports/tasks/{finished.task_id}'",
            f"curl 'http://127.0.0.1:8000/notification-channels/records?user_id={USER_ID}'",
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def _stable_sections() -> dict:
    return {
        "day6_result": {
            "finance": {
                "data": {
                    "summary": "组合总市值约 18.7 万元，第一大持仓集中度偏高，需要关注回撤和行业集中风险。",
                    "risk": {
                        "data": {
                            "risk_flags": [
                                "第一大持仓占比超过 35%",
                                "组合行业集中在消费与新能源，缺少低相关资产缓冲",
                            ]
                        }
                    },
                }
            }
        },
        "day7_result": {
            "summary": "公告雷达识别到 1 条需人工复核事件。",
            "risk_events": [
                {
                    "symbol": "300750.SZ",
                    "risk_label": "股份质押/监管问询",
                    "severity": "high",
                    "evidence": {
                        "title": "关于控股股东部分股份质押及监管问询的公告",
                        "source": "cninfo",
                        "url": "https://www.cninfo.com.cn/",
                    },
                }
            ],
        },
        "day8_result": {
            "summary": "交易复盘生成 2 条人工复核问题。",
            "questions": [
                "请人工复核新能源持仓的仓位上限是否与当前波动率匹配。",
                "请人工复核买入理由是否覆盖公告风险和行业景气回落情形。",
            ],
        },
    }


if __name__ == "__main__":
    main()
