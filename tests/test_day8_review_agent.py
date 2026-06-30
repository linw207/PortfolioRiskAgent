from __future__ import annotations

import unittest

from config.settings import VectorSettings
from src.app.service.announcement_rag_service import AnnouncementRAGService
from src.app.service.portfolio_service import PortfolioService
from src.app.service.task_service import TaskService
from src.app.service.trade_journal_service import TradeJournalService
from src.app.service.trade_review_service import TradeReviewService
from src.app.service.vector_memory_service import VectorMemoryService
from src.domain.entity import TaskStatus
from src.infra.adapter.mcp import MCPToolRegistry
from src.infra.adapter.mcp.announcement_toolkit import register_announcement_tools
from src.infra.adapter.mcp.financial_toolkit import register_financial_tools
from src.infra.adapter.mcp.review_toolkit import register_review_tools
from src.infra.external.market_data_gateway import MarketDataGateway
from src.infra.repo.mem import MemUnitOfWork


class FakeVector:
    def __init__(self) -> None:
        self.documents: dict[str, dict] = {}

    def upsert(self, collection_name, ids, documents, metadatas, embeddings):
        for index, item_id in enumerate(ids):
            self.documents[item_id] = {
                "collection": collection_name,
                "document": documents[index],
                "metadata": metadatas[index],
                "embedding": embeddings[index],
            }
        return {"collection": collection_name, "ids": ids, "status": 200, "body": ""}

    def query(self, collection_name, query_embeddings, n_results=5, where=None):
        matches = [
            (item_id, item)
            for item_id, item in self.documents.items()
            if item["collection"] == collection_name and _matches_where(item["metadata"], where)
        ][:n_results]
        return {
            "ids": [[item_id for item_id, _ in matches]],
            "documents": [[item["document"] for _, item in matches]],
            "metadatas": [[item["metadata"] for _, item in matches]],
            "distances": [[0.1 for _ in matches]],
        }


def _matches_where(metadata: dict, where: dict | None) -> bool:
    if not where:
        return True
    if "$and" in where:
        return all(_matches_where(metadata, item) for item in where["$and"])
    return all(metadata.get(key) == value for key, value in where.items())


def _fake_embed(text: str) -> list[float]:
    return [float(len(text) % 10), 1.0, 0.5]


class DayEightReviewAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.uow = MemUnitOfWork()
        self.registry = MCPToolRegistry(self.uow)
        self.vector = FakeVector()
        self.vector_memory = VectorMemoryService(VectorSettings(), self.vector, _fake_embed)
        self.market_data = MarketDataGateway()
        self.review_service = TradeReviewService(self.uow, self.vector_memory)
        register_financial_tools(self.registry, self.market_data)
        register_announcement_tools(self.registry, AnnouncementRAGService(self.market_data, self.vector_memory))
        register_review_tools(self.registry, self.review_service)

    def _create_portfolio_and_journal(self):
        portfolio = PortfolioService(self.uow).create_portfolio(
            user_id="u_day8",
            name="Day8 组合",
            holdings_payload=[{"symbol": "300750", "shares": 100, "cost_price": 235, "name": "宁德时代"}],
        )
        TradeJournalService(self.uow).add_journal(
            "u_day8",
            {
                "symbol": "300750",
                "action": "buy",
                "trade_date": "2026-05-01",
                "price": 235,
                "shares": 100,
                "reason": "看好成长和业绩增长，长期持有。",
            },
        )
        return portfolio

    def test_search_trade_journals_tool(self) -> None:
        self._create_portfolio_and_journal()
        result = self.registry.call("search_trade_journals", {"user_id": "u_day8", "symbol": "300750"}, task_id="task_day8")
        self.assertTrue(result.success)
        self.assertEqual(len(result.data["journals"]), 1)
        self.assertEqual(result.data["journals"][0]["action"], "buy")
        self.assertEqual(self.uow.tool_calls.list_by_task("task_day8")[-1].tool_name, "search_trade_journals")

    def test_reflection_generates_human_review_question(self) -> None:
        result = self.review_service.reflect_trade_journal(
            journal={"symbol": "300750.SZ", "action": "buy", "reason": "看好成长和业绩增长"},
            current_facts={
                "financial_metrics": {"net_profit_growth": -0.12, "revenue_growth": -0.08},
                "quote": {"change_pct": -0.035},
                "announcement_events": [{"risk_label": "股份质押", "evidence": {"title": "股份质押公告"}}],
            },
            historical_memories=[],
        )
        self.assertTrue(result["needs_human_review"])
        self.assertTrue(any(question.startswith("请人工复核") for question in result["questions"]))
        self.assertGreaterEqual(len(result["questions"]), 2)

    def test_review_agent_saves_memory_and_task_result(self) -> None:
        portfolio = self._create_portfolio_and_journal()
        task = TaskService(self.uow, self.registry).create_task("u_day8", portfolio.portfolio_id)
        completed = TaskService(self.uow, self.registry).run_review_check(task.task_id)
        self.assertEqual(completed.status, TaskStatus.COMPLETED)
        result = completed.metadata["day8_result"]
        self.assertGreaterEqual(result["question_count"], 1)
        self.assertTrue(any(question.startswith("请人工复核") for question in result["questions"]))
        memory_docs = [
            item
            for item in self.vector.documents.values()
            if item["collection"] == VectorSettings().collection_memory and item["metadata"].get("memory_type") == "trade_review"
        ]
        self.assertGreaterEqual(len(memory_docs), 1)
        agents = [item.agent_name for item in self.uow.agent_runs.list_by_task(task.task_id)]
        self.assertIn("ReviewAgent", agents)
        tool_names = [item.tool_name for item in self.uow.tool_calls.list_by_task(task.task_id)]
        self.assertIn("reflect_trade_journal", tool_names)
        self.assertIn("save_risk_memory", tool_names)


if __name__ == "__main__":
    unittest.main()
