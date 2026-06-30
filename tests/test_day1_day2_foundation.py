from __future__ import annotations

import unittest

from src.app.service.validation import normalize_symbol
from src.factory import create_container


class DayOneDayTwoFoundationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.container = create_container()

    def test_health_exposes_external_boundaries(self) -> None:
        health = self.container.health_service.health()
        self.assertEqual(health["status"], "ok")
        self.assertIn("mongo", health)
        self.assertIn("redis", health)
        self.assertIn("vector", health)
        self.assertIn("model", health)

    def test_portfolio_create_and_list(self) -> None:
        portfolio = self.container.portfolio_service.create_portfolio(
            user_id="u1",
            name="day2组合",
            holdings_payload=[
                {
                    "symbol": "300750",
                    "shares": 100,
                    "cost_price": 235,
                    "buy_reason": "看好新能源龙头",
                    "max_loss_limit": "0.12",
                }
            ],
        )
        self.assertEqual(portfolio.holdings[0].symbol, "300750.SZ")
        self.assertEqual(len(self.container.portfolio_service.list_portfolios("u1")), 1)

    def test_csv_import_with_chinese_headers(self) -> None:
        result = self.container.portfolio_service.import_csv(
            user_id="u1",
            filename="sample.csv",
            content="股票代码,持仓数量,成本价,买入理由\n600519,10,1520,高ROE消费龙头\n".encode(),
        )
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["portfolio"].holdings[0].symbol, "600519.SH")

    def test_watch_trade_task_notification_schedule(self) -> None:
        portfolio = self.container.portfolio_service.create_portfolio(
            user_id="u1",
            name="基础接口组合",
            holdings_payload=[{"symbol": "000001", "shares": 1000, "cost_price": 10.8}],
        )
        watch = self.container.watch_service.add_watch_item("u1", {"symbol": "300750", "tags": ["新能源"]})
        journal = self.container.trade_journal_service.add_journal(
            "u1",
            {
                "symbol": "300750",
                "action": "buy",
                "trade_date": "2026-06-24",
                "price": 235,
                "shares": 100,
                "reason": "建立复盘基线",
            },
        )
        task = self.container.task_service.create_task("u1", portfolio.portfolio_id)
        channel = self.container.notification_service.create_channel(
            "u1",
            {
                "channel_type": "feishu",
                "channel_name": "风险提醒群",
                "webhook_url": "https://example.com/webhook",
                "event_types": ["report_ready"],
            },
        )
        schedule = self.container.schedule_service.create_job(
            "u1",
            {"job_type": "daily_portfolio_check", "target_id": portfolio.portfolio_id, "enabled": True},
        )
        self.assertEqual(watch.symbol, "300750.SZ")
        self.assertEqual(journal.symbol, "300750.SZ")
        self.assertEqual(task.status, "pending")
        self.assertEqual(channel.channel_type, "feishu")
        self.assertEqual(schedule.status, "enabled")

    def test_symbol_validation(self) -> None:
        self.assertEqual(normalize_symbol("600519"), "600519.SH")
        self.assertEqual(normalize_symbol("000001"), "000001.SZ")
        with self.assertRaises(ValueError):
            normalize_symbol("AAPL")


if __name__ == "__main__":
    unittest.main()
