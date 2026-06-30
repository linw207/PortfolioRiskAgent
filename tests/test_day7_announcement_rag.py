from __future__ import annotations

import unittest

from config.settings import VectorSettings
from src.app.service.announcement_rag_service import AnnouncementRAGService
from src.app.service.portfolio_service import PortfolioService
from src.app.service.task_service import TaskService
from src.app.service.vector_memory_service import VectorMemoryService
from src.domain.entity import TaskStatus
from src.infra.adapter.mcp import MCPToolRegistry
from src.infra.adapter.mcp.announcement_toolkit import register_announcement_tools
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


class FakeMarketDataGateway:
    def announcements(self, symbol: str, limit: int = 10, keywords: list[str] | None = None):
        data = [
            {
                "symbol": symbol,
                "title": "关于控股股东部分股份质押的公告",
                "published_at": "2026-06-05",
                "source": "fake_announcement",
                "url": "fake://pledge",
                "content": "控股股东股份质押，本次质押用途为补充流动资金。",
            },
            {
                "symbol": symbol,
                "title": "关于收到交易所问询函的公告",
                "published_at": "2026-05-21",
                "source": "fake_announcement",
                "url": "fake://inquiry",
                "content": "交易所问询函要求说明收入确认和存货跌价准备。",
            },
        ]
        if keywords:
            data = [item for item in data if any(keyword in item["title"] or keyword in item["content"] for keyword in keywords)]
        return data[:limit], "fake_announcement", True


def _matches_where(metadata: dict, where: dict | None) -> bool:
    if not where:
        return True
    if "$and" in where:
        return all(_matches_where(metadata, item) for item in where["$and"])
    return all(metadata.get(key) == value for key, value in where.items())


def _fake_embed(text: str) -> list[float]:
    return [float(len(text) % 10), 1.0, 0.5]


class DaySevenAnnouncementRAGTest(unittest.TestCase):
    def setUp(self) -> None:
        self.uow = MemUnitOfWork()
        self.registry = MCPToolRegistry(self.uow)
        self.vector_memory = VectorMemoryService(VectorSettings(), FakeVector(), _fake_embed)
        self.rag = AnnouncementRAGService(FakeMarketDataGateway(), self.vector_memory)
        register_announcement_tools(self.registry, self.rag)

    def test_ingest_chunks_and_marks_risk_keywords(self) -> None:
        result = self.rag.ingest_symbol_announcements("300750", limit=10)
        self.assertEqual(result["symbol"], "300750.SZ")
        self.assertGreaterEqual(result["chunk_count"], 2)
        keywords = {keyword for chunk in result["chunks"] for keyword in chunk["risk_keywords"]}
        self.assertIn("质押", keywords)
        self.assertIn("问询", keywords)

    def test_retrieve_announcement_evidence_tool_records_call(self) -> None:
        result = self.registry.call(
            "retrieve_announcement_evidence",
            {"symbol": "300750", "risk_keywords": ["质押"], "limit": 3},
            task_id="task_day7",
        )
        self.assertTrue(result.success)
        evidence = result.data["evidence"]
        self.assertGreaterEqual(len(evidence), 1)
        self.assertIn("质押", evidence[0]["matched_keywords"])
        records = self.uow.tool_calls.list_by_task("task_day7")
        self.assertEqual(records[-1].tool_name, "retrieve_announcement_evidence")

    def test_announcement_agent_task_outputs_events_and_evidence(self) -> None:
        portfolio = PortfolioService(self.uow).create_portfolio(
            user_id="u_day7",
            name="Day7 组合",
            holdings_payload=[{"symbol": "300750", "shares": 100, "cost_price": 235, "name": "宁德时代"}],
        )
        task = TaskService(self.uow, self.registry).create_task("u_day7", portfolio.portfolio_id)
        completed = TaskService(self.uow, self.registry).run_announcement_check(task.task_id)
        self.assertEqual(completed.status, TaskStatus.COMPLETED)
        result = completed.metadata["day7_result"]
        self.assertGreaterEqual(result["risk_event_count"], 2)
        labels = {event["risk_label"] for event in result["risk_events"]}
        self.assertIn("股份质押", labels)
        self.assertIn("监管问询", labels)
        self.assertTrue(result["risk_events"][0]["evidence"]["snippet"])
        agents = [item.agent_name for item in self.uow.agent_runs.list_by_task(task.task_id)]
        self.assertIn("AnnouncementAgent", agents)


if __name__ == "__main__":
    unittest.main()
