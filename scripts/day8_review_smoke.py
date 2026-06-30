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
        user_id="day8_smoke_user",
        name="Day8 Review Smoke",
        holdings_payload=[{"symbol": "300750", "shares": 100, "cost_price": 235, "name": "宁德时代"}],
    )
    container.trade_journal_service.add_journal(
        "day8_smoke_user",
        {
            "symbol": "300750",
            "action": "buy",
            "trade_date": "2026-05-01",
            "price": 235,
            "shares": 100,
            "reason": "看好成长和业绩增长，长期持有。",
            "review_after_days": 7,
        },
    )
    task = container.task_service.create_task("day8_smoke_user", portfolio.portfolio_id)
    completed = container.task_service.run_review_check(task.task_id)
    result = completed.metadata.get("day8_result", {})
    print("task_status=", completed.status)
    print("question_count=", result.get("question_count"))
    print("summary=", result.get("summary"))
    if result.get("questions"):
        print("first_question=", result["questions"][0])
    memory = container.vector_memory_service.search_agent_memory(
        query="300750 交易复盘 成长 业绩",
        user_id="day8_smoke_user",
        symbol="300750.SZ",
        limit=3,
    )
    print("memory_hits=", len(memory.get("items", [])))


if __name__ == "__main__":
    main()
