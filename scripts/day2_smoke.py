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
        user_id="user_demo",
        name="Day2 smoke portfolio",
        holdings_payload=[
            {"symbol": "300750", "shares": 100, "cost_price": 235, "buy_reason": "看好新能源长期需求"},
            {"symbol": "000001", "shares": 1000, "cost_price": 10.8, "buy_reason": "低估值分散波动"},
        ],
    )
    task = container.task_service.create_task("user_demo", portfolio.portfolio_id)
    print("health_keys=", sorted(container.health_service.health().keys()))
    print("portfolio_id=", portfolio.portfolio_id)
    print("task_id=", task.task_id)
    print("task_status=", task.status)


if __name__ == "__main__":
    main()
