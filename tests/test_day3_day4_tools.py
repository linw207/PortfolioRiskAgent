from __future__ import annotations

import unittest

from src.factory import create_container


class DayThreeDayFourToolsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.container = create_container()

    def test_tool_discovery_contains_day4_tools(self) -> None:
        names = {tool["name"] for tool in self.container.tool_service.list_tools()}
        self.assertIn("get_stock_price", names)
        self.assertIn("get_index_price", names)
        self.assertIn("get_financial_metrics", names)
        self.assertIn("calculate_portfolio_risk", names)
        self.assertIn("search_announcements", names)
        self.assertIn("retrieve_evidence", names)
        self.assertIn("web_search", names)
        self.assertIn("trusted_news_search", names)
        self.assertIn("trusted_announcement_search", names)

    def test_tool_argument_validation_and_call_record(self) -> None:
        result = self.container.tool_service.call_tool("get_stock_price", {})
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "INVALID_ARGUMENTS")
        records = self.container.uow.tool_calls.list_by_task("")
        self.assertEqual(records[-1].tool_name, "get_stock_price")
        self.assertFalse(records[-1].success)

    def test_stock_price_tool_uses_fallback_when_akshare_unavailable(self) -> None:
        result = self.container.tool_service.call_tool("get_stock_price", {"symbol": "300750"})
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["symbol"], "300750.SZ")
        self.assertIn(result["source"], {"AKShare", "local_sample"})

    def test_portfolio_risk_tool(self) -> None:
        result = self.container.tool_service.call_tool(
            "calculate_portfolio_risk",
            {
                "holdings": [
                    {"symbol": "300750", "shares": 100, "cost_price": 235, "name": "宁德时代"},
                    {"symbol": "000001", "shares": 1000, "cost_price": 10.8, "name": "平安银行"},
                ]
            },
        )
        self.assertTrue(result["success"])
        self.assertGreater(result["data"]["total_market_value"], 0)
        self.assertIn("positions", result["data"])

    def test_announcement_evidence_tool(self) -> None:
        result = self.container.tool_service.call_tool("retrieve_evidence", {"symbol": "300750", "limit": 5})
        self.assertTrue(result["success"])
        self.assertGreaterEqual(len(result["data"]["evidence"]), 1)

    def test_json_action_fallback(self) -> None:
        payload = '{"思考":"需要获取行情","动作":"get_stock_price","参数":{"symbol":"600519"}}'
        result = self.container.tool_service.call_json_action(payload)
        self.assertEqual(result["action"], "get_stock_price")
        self.assertTrue(result["result"]["success"])

    def test_search_tool_without_keys_returns_configuration_message(self) -> None:
        result = self.container.tool_service.call_tool("web_search", {"query": "宁德时代 最新公告", "max_results": 3})
        if self.container.search_gateway.available_backends:
            if result["success"]:
                self.assertIn(result["source"], {"tavily", "serpapi"})
            else:
                self.assertEqual(result["error_code"], "SEARCH_BACKEND_UNAVAILABLE")
        else:
            self.assertFalse(result["success"])
            self.assertEqual(result["error_code"], "SEARCH_BACKEND_UNAVAILABLE")
            self.assertIn("TAVILY_API_KEY", result["error_message"])

    def test_trusted_announcement_search_tool_is_registered_and_audited(self) -> None:
        result = self.container.tool_service.call_tool(
            "trusted_announcement_search",
            {"symbol": "300750", "company_name": "宁德时代", "keywords": ["问询函", "质押"]},
            task_id="task_search_test",
        )
        records = self.container.uow.tool_calls.list_by_task("task_search_test")
        self.assertEqual(records[-1].tool_name, "trusted_announcement_search")
        if not self.container.search_gateway.available_backends:
            self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
