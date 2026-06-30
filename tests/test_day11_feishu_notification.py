from __future__ import annotations

import unittest

from src.app.service.notification_service import NotificationService
from src.infra.external.feishu_client import FeishuCLIClient
from src.infra.repo.mem import MemUnitOfWork


class FlakyFeishuBot:
    def __init__(self) -> None:
        self.calls = 0

    def send_text(self, webhook_url: str, title: str, content: str, secret: str = ""):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary feishu failure")
        return {"ok": True, "fake": True, "title": title}


class FakeFeishuCLI:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    def status(self):
        return {"installed": True, "authenticated": True}

    def send_text_to_user(self, user_open_id: str, title: str, content: str):
        self.sent.append({"user_open_id": user_open_id, "title": title, "content": content})
        return {"ok": True, "fake": True}


class DayElevenFeishuNotificationTest(unittest.TestCase):
    def test_feishu_test_send_uses_mock_webhook(self) -> None:
        service = NotificationService(MemUnitOfWork())
        channel = service.create_channel(
            "u_day11",
            {
                "channel_type": "feishu",
                "channel_name": "飞书测试群",
                "webhook_url": "mock://feishu-test",
                "event_types": ["report_ready", "task_failed"],
            },
        )
        record = service.send_test(channel.channel_id)
        self.assertEqual(record.status, "sent")
        self.assertEqual(record.event_type, "test")
        self.assertTrue(record.metadata["response"]["dry_run"])

    def test_dispatch_event_filters_channels_and_sends(self) -> None:
        service = NotificationService(MemUnitOfWork())
        service.create_channel(
            "u_day11",
            {"channel_type": "feishu", "channel_name": "报告群", "webhook_url": "mock://report", "event_types": ["report_ready"]},
        )
        service.create_channel(
            "u_day11",
            {"channel_type": "feishu", "channel_name": "失败群", "webhook_url": "mock://failed", "event_types": ["task_failed"]},
        )
        records = service.dispatch_event("u_day11", "report_ready", "体检完成", "报告已生成")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].status, "sent")
        self.assertEqual(len(service.list_records("u_day11")), 1)

    def test_retry_failed_notification(self) -> None:
        service = NotificationService(MemUnitOfWork(), feishu_bot=FlakyFeishuBot())
        channel = service.create_channel(
            "u_day11",
            {"channel_type": "feishu", "channel_name": "重试群", "webhook_url": "https://example.invalid", "event_types": ["report_ready"]},
        )
        record = service.record_event("u_day11", "report_ready", "体检完成", "报告已生成")[0]
        failed = service.send_record(record.record_id, raise_on_error=False)
        self.assertEqual(failed.status, "failed")
        self.assertEqual(failed.retry_count, 1)
        result = service.retry_failed()
        self.assertEqual(result["sent_count"], 1)
        self.assertEqual(result["records"][0].status, "sent")
        self.assertEqual(channel.channel_type, "feishu")

    def test_feishu_cli_channel_sends_to_user_open_id(self) -> None:
        fake_cli = FakeFeishuCLI()
        service = NotificationService(MemUnitOfWork(), feishu_cli=fake_cli)
        channel = service.create_channel(
            "u_day11",
            {
                "channel_type": "feishu_cli",
                "channel_name": "CLI 私聊",
                "user_open_id": "ou_test",
                "event_types": ["report_ready"],
            },
        )
        records = service.dispatch_event("u_day11", "report_ready", "体检完成", "报告已生成")
        self.assertEqual(records[0].status, "sent")
        self.assertEqual(channel.webhook_url, "ou_test")
        self.assertEqual(fake_cli.sent[0]["user_open_id"], "ou_test")

    def test_cli_status_has_install_guidance_when_unavailable(self) -> None:
        status = FeishuCLIClient().status()
        self.assertIn("installed", status)
        if not status["installed"]:
            self.assertIn("npm install -g @larksuite/cli", status["install_commands"])


if __name__ == "__main__":
    unittest.main()
