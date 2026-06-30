from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.factory import create_container


def main() -> None:
    container = create_container()
    portfolio = container.portfolio_service.create_portfolio(
        user_id="redis_chroma_smoke_user",
        name="Redis Chroma Smoke",
        holdings_payload=[{"symbol": "300750", "shares": 100, "cost_price": 235, "name": "宁德时代"}],
    )
    task = container.task_service.create_task("redis_chroma_smoke_user", portfolio.portfolio_id)
    status = container.redis_runtime_service.get_task_status(task.task_id)
    queued = container.redis_runtime_service.pop_analysis_task()
    print("redis_status_task_id=", status["task_id"] if status else "")
    print("redis_popped_task_id=", queued)

    upsert = container.vector_memory_service.upsert_announcement_chunks(
        [
            {
                "chunk_id": "smoke_300750_pledge",
                "symbol": "300750.SZ",
                "title": "宁德时代股份质押公告",
                "published_at": "2026-06-26",
                "source": "smoke",
                "url": "smoke://announcement/300750/pledge",
                "risk_keywords": ["质押"],
                "text": "宁德时代控股股东股份质押事项，需要关注流动性与质押比例变化。",
            }
        ]
    )
    result = container.vector_memory_service.search_announcement_chunks("宁德时代 质押 风险", symbol="300750.SZ", limit=3)
    print("chroma_upsert_ids=", ",".join(upsert["ids"]))
    print("chroma_hits=", len(result["items"]))
    if result["items"]:
        print("chroma_first_title=", result["items"][0]["metadata"].get("title", ""))


if __name__ == "__main__":
    main()
