from __future__ import annotations

import unittest

from src.domain.entity import TaskStatus
from src.factory import create_container


class DaySixAgentsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.container = create_container()

    def _create_task(self):
        portfolio = self.container.portfolio_service.create_portfolio(
            user_id="u_day6",
            name="Day6 组合",
            holdings_payload=[
                {"symbol": "300750", "shares": 100, "cost_price": 235, "name": "宁德时代"},
                {"symbol": "000001", "shares": 1000, "cost_price": 10.8, "name": "平安银行"},
            ],
        )
        return self.container.task_service.create_task("u_day6", portfolio.portfolio_id)

    def test_orchestrator_calls_finance_agent_as_tool(self) -> None:
        task = self._create_task()
        completed = self.container.task_service.run_finance_check(task.task_id)
        self.assertEqual(completed.status, TaskStatus.COMPLETED)
        self.assertEqual(completed.completed_steps, 2)
        self.assertIn("day6_result", completed.metadata)
        finance = completed.metadata["day6_result"]["finance"]
        self.assertTrue(finance["success"])
        self.assertIn("summary", finance["data"])
        self.assertGreater(finance["data"]["risk"]["data"]["total_market_value"], 0)

        runs = self.container.uow.agent_runs.list_by_task(task.task_id)
        agents = [item.agent_name for item in runs]
        self.assertIn("OrchestratorAgent", agents)
        self.assertIn("FinanceAgent", agents)
        actions = [item.action for item in runs]
        self.assertIn("run_finance_agent", actions)
        self.assertIn("calculate_portfolio_risk", actions)

        tool_calls = self.container.uow.tool_calls.list_by_task(task.task_id)
        tool_names = [item.tool_name for item in tool_calls]
        self.assertIn("run_finance_agent", tool_names)
        self.assertIn("calculate_portfolio_risk", tool_names)
        self.assertIn("get_stock_price", tool_names)
        self.assertIn("get_financial_metrics", tool_names)

    def test_finance_agent_tool_is_registered_after_run(self) -> None:
        task = self._create_task()
        self.assertIsNone(self.container.tool_registry.get("run_finance_agent"))
        self.container.task_service.run_finance_check(task.task_id)
        self.assertIsNotNone(self.container.tool_registry.get("run_finance_agent"))


if __name__ == "__main__":
    unittest.main()
