from __future__ import annotations

import json
import unittest

from config.settings import RedisSettings, VectorSettings
from src.app.service.redis_runtime_service import RedisRuntimeService
from src.app.service.vector_memory_service import VectorMemoryService
from src.domain.entity import AnalysisTask


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}

    def set_value(self, key: str, value: str, ex: int | None = None, nx: bool = False) -> bool:
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    def get_value(self, key: str) -> str | None:
        return self.values.get(key)

    def delete(self, key: str) -> int:
        return 1 if self.values.pop(key, None) is not None else 0

    def lpush(self, key: str, value: str) -> int:
        self.lists.setdefault(key, []).insert(0, value)
        return len(self.lists[key])

    def rpop(self, key: str) -> str | None:
        if not self.lists.get(key):
            return None
        return self.lists[key].pop()

    def llen(self, key: str) -> int:
        return len(self.lists.get(key, []))


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


class RedisChromaRuntimeTest(unittest.TestCase):
    def test_redis_task_status_queue_and_lock(self) -> None:
        redis = RedisRuntimeService(RedisSettings(), FakeRedis())
        task = AnalysisTask(user_id="u", portfolio_id="p")
        redis.save_task_status(task)
        loaded = redis.get_task_status(task.task_id)
        self.assertEqual(loaded["task_id"], task.task_id)
        self.assertEqual(redis.enqueue_analysis_task(task.task_id), 1)
        self.assertEqual(redis.analysis_queue_size(), 1)
        self.assertEqual(redis.pop_analysis_task(), task.task_id)
        self.assertTrue(redis.acquire_schedule_lock("daily_portfolio_check", "p"))
        self.assertFalse(redis.acquire_schedule_lock("daily_portfolio_check", "p"))
        self.assertEqual(redis.release_schedule_lock("daily_portfolio_check", "p"), 1)

    def test_vector_announcement_upsert_and_search(self) -> None:
        service = VectorMemoryService(VectorSettings(), FakeVector())
        upsert = service.upsert_announcement_chunks(
            [
                {
                    "chunk_id": "c1",
                    "symbol": "300750.SZ",
                    "title": "宁德时代质押公告",
                    "text": "宁德时代股份质押风险提示",
                    "risk_keywords": ["质押"],
                }
            ]
        )
        self.assertEqual(upsert["ids"], ["c1"])
        result = service.search_announcement_chunks("宁德时代 质押", symbol="300750.SZ")
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["metadata"]["symbol"], "300750.SZ")


if __name__ == "__main__":
    unittest.main()
