from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.factory import create_container


def main() -> None:
    container = create_container()
    health = container.ollama.health()
    print("ollama_available=", health.get("available"))
    print("embedding_model=", health.get("configured_embedding_model"))

    portfolio = container.portfolio_service.create_portfolio(
        user_id="day7_smoke_user",
        name="Day7 Announcement Smoke",
        holdings_payload=[{"symbol": "300750", "shares": 100, "cost_price": 235, "name": "宁德时代"}],
    )
    task = container.task_service.create_task("day7_smoke_user", portfolio.portfolio_id)
    completed = container.task_service.run_announcement_check(task.task_id)
    result = completed.metadata.get("day7_result", {})
    print("task_status=", completed.status)
    print("risk_event_count=", result.get("risk_event_count"))
    print("summary=", result.get("summary"))
    if result.get("risk_events"):
        first = result["risk_events"][0]
        print("first_risk_label=", first.get("risk_label"))
        print("first_evidence_title=", first.get("evidence", {}).get("title"))


if __name__ == "__main__":
    main()
