from __future__ import annotations

from typing import Any

from src.domain.entity import NotificationChannel, NotificationRecord
from src.domain.time import now_iso
from src.infra.external.feishu_client import FeishuBotClient, FeishuCLIClient
from src.infra.repo.mem import MemUnitOfWork


class NotificationService:
    def __init__(
        self,
        uow: MemUnitOfWork,
        feishu_bot: FeishuBotClient | None = None,
        feishu_cli: FeishuCLIClient | None = None,
    ) -> None:
        self.uow = uow
        self.feishu_bot = feishu_bot or FeishuBotClient()
        self.feishu_cli = feishu_cli or FeishuCLIClient()

    def create_channel(self, user_id: str, payload: dict[str, Any]) -> NotificationChannel:
        if not payload.get("channel_name"):
            raise ValueError("渠道名称不能为空")
        channel_type = payload["channel_type"]
        if channel_type not in {"feishu", "feishu_cli"}:
            raise ValueError("Day11 仅支持飞书通知渠道")
        webhook_url = payload.get("webhook_url") or payload.get("user_open_id")
        if not webhook_url:
            raise ValueError("飞书 webhook 地址或 user_open_id 不能为空")
        channel = NotificationChannel(
            user_id=user_id,
            channel_type=channel_type,
            channel_name=payload["channel_name"],
            webhook_url=webhook_url,
            secret=payload.get("secret", ""),
            enabled=bool(payload.get("enabled", True)),
            event_types=list(payload.get("event_types", [])),
        )
        return self.uow.notifications.save_channel(channel)

    def list_channels(self, user_id: str) -> list[NotificationChannel]:
        return self.uow.notifications.list_channels(user_id)

    def list_records(self, user_id: str) -> list[NotificationRecord]:
        return self.uow.notifications.list_records(user_id)

    def get_cli_status(self) -> dict[str, Any]:
        return self.feishu_cli.status()

    def record_event(
        self,
        user_id: str,
        event_type: str,
        title: str,
        content: str,
        status: str = "pending_day11_send",
    ) -> list[NotificationRecord]:
        channels = [
            channel
            for channel in self.uow.notifications.list_channels(user_id)
            if channel.enabled and (not channel.event_types or event_type in channel.event_types)
        ]
        records = []
        for channel in channels:
            records.append(
                self.uow.notifications.save_record(
                    NotificationRecord(
                        channel_id=channel.channel_id,
                        event_type=event_type,
                        title=title,
                        content=content,
                        status=status,
                    )
                )
            )
        return records

    def dispatch_event(self, user_id: str, event_type: str, title: str, content: str) -> list[NotificationRecord]:
        records = self.record_event(user_id, event_type, title, content, status="pending")
        dispatched = []
        for record in records:
            dispatched.append(self.send_record(record.record_id, raise_on_error=False))
        return dispatched

    def send_test(self, channel_id: str) -> NotificationRecord:
        channel = self._get_channel(channel_id)
        record = NotificationRecord(
            channel_id=channel.channel_id,
            event_type="test",
            title="PortfolioRiskAgent 飞书通知测试",
            content="这是一条测试消息，用于验证飞书群机器人 webhook 是否可用。",
            status="pending",
        )
        saved = self.uow.notifications.save_record(record)
        return self.send_record(saved.record_id)

    def send_record(self, record_id: str, raise_on_error: bool = True) -> NotificationRecord:
        record = self.uow.notifications.get_record(record_id)
        if record is None:
            raise ValueError("通知记录不存在")
        channel = self._get_channel(record.channel_id)
        if not channel.enabled:
            record.status = "failed"
            record.error_message = "通知渠道已禁用"
            record.updated_at = now_iso()
            saved = self.uow.notifications.save_record(record)
            if raise_on_error:
                raise ValueError(record.error_message)
            return saved
        try:
            if channel.channel_type == "feishu":
                response = self.feishu_bot.send_text(channel.webhook_url, record.title, record.content, secret=channel.secret)
            elif channel.channel_type == "feishu_cli":
                response = self.feishu_cli.send_text_to_user(channel.webhook_url, record.title, record.content)
            else:
                raise ValueError(f"不支持的通知渠道: {channel.channel_type}")
            if not response.get("ok"):
                raise RuntimeError(str(response))
            record.status = "sent"
            record.error_message = ""
            record.sent_at = now_iso()
            record.metadata["response"] = response
        except Exception as exc:  # noqa: BLE001
            record.status = "failed"
            record.error_message = str(exc)[:500]
            record.retry_count += 1
            if raise_on_error:
                record.updated_at = now_iso()
                self.uow.notifications.save_record(record)
                raise
        record.updated_at = now_iso()
        return self.uow.notifications.save_record(record)

    def retry_failed(self, limit: int = 20) -> dict[str, Any]:
        retried = []
        for record in self.uow.notifications.list_records_by_status("failed")[:limit]:
            retried.append(self.send_record(record.record_id, raise_on_error=False))
        return {
            "retry_count": len(retried),
            "sent_count": len([record for record in retried if record.status == "sent"]),
            "failed_count": len([record for record in retried if record.status == "failed"]),
            "records": retried,
        }

    def _get_channel(self, channel_id: str) -> NotificationChannel:
        channel = self.uow.notifications.get_channel(channel_id)
        if channel is None:
            raise ValueError("通知渠道不存在")
        return channel
