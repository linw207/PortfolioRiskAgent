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
        user_id="day9_smoke_user",
        name="Day9 Report Smoke",
        holdings_payload=[{"symbol": "300750", "shares": 100, "cost_price": 235, "name": "宁德时代"}],
    )
    container.trade_journal_service.add_journal(
        "day9_smoke_user",
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
    task = container.task_service.create_task("day9_smoke_user", portfolio.portfolio_id)
    completed = container.task_service.run_report_check(task.task_id)
    result = completed.metadata.get("day9_result", {})
    report = container.report_archive_service.get_by_task(task.task_id)
    print("task_status=", completed.status)
    print("report_id=", result.get("report_id"))
    print("passed_guardrail=", report.passed_guardrail)
    print("markdown_chars=", len(report.markdown))
    print("has_report_title=", "# Day9 Report Smoke 持仓风险体检报告" in report.markdown)
    print("has_human_review=", "请人工复核" in report.markdown)


if __name__ == "__main__":
    main()
