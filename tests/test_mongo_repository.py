from __future__ import annotations

import importlib.util
import unittest
from dataclasses import replace

from config.settings import get_settings
from src.factory import create_container


@unittest.skipIf(importlib.util.find_spec("pymongo") is None, "pymongo is not installed")
class MongoRepositoryIntegrationTest(unittest.TestCase):
    def test_mongo_unit_of_work_persists_day6_flow(self) -> None:
        settings = replace(get_settings(), use_memory_fallback=False)
        container = create_container(settings)
        try:
            container.mongo.sync_client().admin.command("ping")
        except Exception as exc:  # noqa: BLE001
            self.skipTest(f"MongoDB is not available: {exc}")

        user_id = "mongo_integration_test_user"
        portfolio = container.portfolio_service.create_portfolio(
            user_id=user_id,
            name="Mongo Integration Portfolio",
            holdings_payload=[
                {"symbol": "300750", "shares": 100, "cost_price": 235, "name": "宁德时代"},
                {"symbol": "000001", "shares": 1000, "cost_price": 10.8, "name": "平安银行"},
            ],
        )
        loaded = container.portfolio_service.get_portfolio(portfolio.portfolio_id)
        self.assertEqual(len(loaded.holdings), 2)
        task = container.task_service.create_task(user_id, loaded.portfolio_id)
        completed = container.task_service.run_finance_check(task.task_id)
        self.assertEqual(completed.status, "completed")
        self.assertGreaterEqual(len(container.uow.agent_runs.list_by_task(task.task_id)), 4)
        self.assertGreaterEqual(len(container.uow.tool_calls.list_by_task(task.task_id)), 4)


if __name__ == "__main__":
    unittest.main()
