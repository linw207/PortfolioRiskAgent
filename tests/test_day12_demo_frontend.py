from __future__ import annotations

import unittest

try:
    from fastapi.testclient import TestClient

    from src.api.web.application import create_app
except (ImportError, RuntimeError):  # pragma: no cover - local system Python may not install web test deps
    TestClient = None
    create_app = None


class DayTwelveDemoFrontendTest(unittest.TestCase):
    def setUp(self) -> None:
        if TestClient is None or create_app is None:
            self.skipTest("fastapi is not installed")
        self.client = TestClient(create_app())

    def test_static_demo_app_is_served(self) -> None:
        response = self.client.get("/app")
        self.assertEqual(response.status_code, 200)
        self.assertIn("PortfolioRiskAgent", response.text)

    def test_task_trace_endpoints(self) -> None:
        portfolio_response = self.client.post(
            "/portfolios",
            json={
                "user_id": "u_day12",
                "name": "Day12 组合",
                "holdings": [{"symbol": "300750", "shares": 100, "cost_price": 235, "name": "宁德时代"}],
            },
        )
        portfolio_id = portfolio_response.json()["data"]["portfolio_id"]
        task_response = self.client.post("/tasks", json={"user_id": "u_day12", "portfolio_id": portfolio_id})
        task_id = task_response.json()["data"]["task_id"]

        runs = self.client.get(f"/tasks/{task_id}/agent-runs")
        calls = self.client.get(f"/tasks/{task_id}/tool-calls")
        self.assertEqual(runs.status_code, 200)
        self.assertEqual(calls.status_code, 200)
        self.assertEqual(runs.json()["data"], [])
        self.assertEqual(calls.json()["data"], [])


if __name__ == "__main__":
    unittest.main()
