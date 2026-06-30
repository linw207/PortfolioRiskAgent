from __future__ import annotations

import unittest

from src.app.service.portfolio_service import PortfolioService
from src.app.service.report_archive_service import ReportArchiveService
from src.app.service.report_service import ReportService
from src.app.service.task_service import TaskService
from src.app.service.trade_journal_service import TradeJournalService
from src.domain.entity import TaskStatus
from src.factory import create_container
from src.infra.repo.mem import MemUnitOfWork


class DayNineReportAgentTest(unittest.TestCase):
    def test_guardrail_rewrites_forbidden_phrases(self) -> None:
        service = ReportService(MemUnitOfWork(), ollama=None)
        result = service.guardrail_check("建议买入 300750，目标价 300，保证收益。", use_model=False)
        self.assertFalse(result["passed"])
        self.assertIn("不提供买入建议", result["rewritten_markdown"])
        self.assertIn("不提供目标价", result["rewritten_markdown"])
        self.assertIn("不承诺收益", result["rewritten_markdown"])

    def test_report_agent_generates_and_archives_report(self) -> None:
        container = create_container()
        portfolio = PortfolioService(container.uow).create_portfolio(
            user_id="u_day9",
            name="Day9 组合",
            holdings_payload=[{"symbol": "300750", "shares": 100, "cost_price": 235, "name": "宁德时代"}],
        )
        TradeJournalService(container.uow).add_journal(
            "u_day9",
            {
                "symbol": "300750",
                "action": "buy",
                "trade_date": "2026-05-01",
                "price": 235,
                "shares": 100,
                "reason": "看好成长和业绩增长，长期持有。",
            },
        )
        task = TaskService(container.uow, container.tool_registry).create_task("u_day9", portfolio.portfolio_id)
        task.metadata["day6_result"] = {
            "finance": {
                "data": {
                    "summary": "组合总市值 19680.00 元；总盈亏 -3820.00 元；第一大持仓占比 100.0%；风险标记 1 个。",
                    "risk": {"data": {"risk_flags": ["第一大持仓占比过高"]}},
                }
            }
        }
        task.metadata["day7_result"] = {
            "summary": "检索到公告风险事件 1 条：股份质押 1 条。",
            "risk_events": [
                {
                    "symbol": "300750.SZ",
                    "risk_label": "股份质押",
                    "severity": "medium",
                    "evidence": {"title": "股份质押公告", "source": "unit_test", "url": "test://pledge"},
                }
            ],
        }
        task.metadata["day8_result"] = {
            "summary": "交易复盘生成待人工复核问题 1 个。",
            "questions": ["请人工复核 300750.SZ 的成长假设：当前财务增速出现压力。"],
        }
        container.uow.analysis_tasks.save(task)
        completed = TaskService(container.uow, container.tool_registry).run_report_check(task.task_id)
        self.assertEqual(completed.status, TaskStatus.COMPLETED)
        result = completed.metadata["day9_result"]
        self.assertIn("report_id", result)
        report = ReportArchiveService(container.uow).get_by_task(task.task_id)
        self.assertEqual(report.report_id, result["report_id"])
        self.assertIn("# Day9 组合 持仓风险体检报告", report.markdown)
        self.assertIn("## 三、公告风险事件", report.markdown)
        self.assertIn("## 四、交易复盘与待人工复核问题", report.markdown)
        self.assertNotIn("建议买入", report.markdown)
        tool_names = [item.tool_name for item in container.uow.tool_calls.list_by_task(task.task_id)]
        self.assertIn("render_report", tool_names)
        self.assertIn("guardrail_check", tool_names)
        self.assertIn("save_report", tool_names)

    def test_manual_report_check_dispatches_report_ready_notification(self) -> None:
        container = create_container()
        portfolio = PortfolioService(container.uow).create_portfolio(
            user_id="u_day9_notify",
            name="Day9 通知组合",
            holdings_payload=[{"symbol": "300750", "shares": 100, "cost_price": 235, "name": "宁德时代"}],
        )
        container.notification_service.create_channel(
            "u_day9_notify",
            {
                "channel_type": "feishu",
                "channel_name": "报告通知",
                "webhook_url": "mock://manual-report",
                "event_types": ["report_ready"],
            },
        )
        task = container.task_service.create_task("u_day9_notify", portfolio.portfolio_id)
        task.metadata["day6_result"] = {"finance": {"data": {"summary": "组合风险摘要。", "risk": {"data": {"risk_flags": []}}}}}
        task.metadata["day7_result"] = {"summary": "暂无公告风险。", "risk_events": []}
        task.metadata["day8_result"] = {"summary": "暂无复盘问题。", "questions": []}
        container.uow.analysis_tasks.save(task)

        completed = container.task_service.run_report_check(task.task_id, notify=True)

        self.assertEqual(completed.status, TaskStatus.COMPLETED)
        records = container.notification_service.list_records("u_day9_notify")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].event_type, "report_ready")
        self.assertEqual(records[0].status, "sent")


if __name__ == "__main__":
    unittest.main()
