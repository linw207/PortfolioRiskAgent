from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.factory import create_container


def main() -> None:
    container = create_container()
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL", "mock://day11-feishu")
    secret = os.getenv("FEISHU_WEBHOOK_SECRET", "")
    channel = container.notification_service.create_channel(
        "day11_smoke_user",
        {
            "channel_type": "feishu",
            "channel_name": "Day11 飞书通知",
            "webhook_url": webhook_url,
            "secret": secret,
            "event_types": ["report_ready", "high_risk_event", "task_failed", "trade_review_reminder"],
        },
    )
    test_record = container.notification_service.send_test(channel.channel_id)
    event_records = container.notification_service.dispatch_event(
        "day11_smoke_user",
        "report_ready",
        "PortfolioRiskAgent 体检完成",
        "报告已生成，请在系统内查看详情。本消息为 Day11 通知链路验证。",
    )
    retry = container.notification_service.retry_failed()
    cli_status = container.notification_service.get_cli_status()
    print("channel_id=", channel.channel_id)
    print("test_status=", test_record.status)
    print("event_records=", len(event_records))
    print("event_status=", event_records[0].status if event_records else "")
    print("retry_failed_count=", retry["failed_count"])
    print("feishu_cli_installed=", cli_status.get("installed"))
    print("feishu_cli_authenticated=", cli_status.get("authenticated"))


if __name__ == "__main__":
    main()
