from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import get_settings
from src.factory import create_container


def main() -> None:
    settings = replace(get_settings(), use_memory_fallback=False)
    container = create_container(settings)
    user_id = "mongo_smoke_user"
    portfolio = container.portfolio_service.create_portfolio(
        user_id=user_id,
        name="Mongo Repo Smoke",
        holdings_payload=[
            {"symbol": "300750", "shares": 100, "cost_price": 235, "name": "宁德时代"},
            {"symbol": "000001", "shares": 1000, "cost_price": 10.8, "name": "平安银行"},
        ],
    )
    loaded = container.portfolio_service.get_portfolio(portfolio.portfolio_id)
    task = container.task_service.create_task(user_id, loaded.portfolio_id)
    completed = container.task_service.run_finance_check(task.task_id)
    print("portfolio_id=", loaded.portfolio_id)
    print("holdings=", len(loaded.holdings))
    print("task_id=", completed.task_id)
    print("task_status=", completed.status)
    print("agent_runs=", len(container.uow.agent_runs.list_by_task(completed.task_id)))
    print("tool_calls=", len(container.uow.tool_calls.list_by_task(completed.task_id)))


if __name__ == "__main__":
    main()
