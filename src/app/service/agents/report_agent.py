from __future__ import annotations

from typing import Any

from src.app.service.agents.announcement_agent import AnnouncementAgent
from src.app.service.agents.finance_agent import FinanceAgent
from src.app.service.agents.review_agent import ReviewAgent
from src.domain.entity import AgentRunRecord, AnalysisTask, Portfolio
from src.infra.adapter.mcp import MCPToolRegistry
from src.infra.repo.mem import MemUnitOfWork


class ReportAgent:
    name = "ReportAgent"

    def __init__(self, registry: MCPToolRegistry, uow: MemUnitOfWork) -> None:
        self.registry = registry
        self.uow = uow

    def run(self, task: AnalysisTask, portfolio: Portfolio) -> dict[str, Any]:
        self._record(
            task.task_id,
            thought="报告必须基于已审计工具输出，先补齐金融、公告和复盘章节，再进行安全审查。",
            action="report_start",
            observation="准备生成 Markdown 报告。",
        )
        sections = self._collect_sections(task, portfolio)
        rendered = self.registry.call("render_report", {"portfolio": portfolio, "sections": sections}, task_id=task.task_id).to_dict()
        if not rendered.get("success"):
            raise RuntimeError(rendered.get("error_message") or "报告渲染失败")
        markdown = rendered["data"]["markdown"]

        guardrail = self.registry.call("guardrail_check", {"markdown": markdown, "use_model": True}, task_id=task.task_id).to_dict()
        if not guardrail.get("success"):
            raise RuntimeError(guardrail.get("error_message") or "报告安全审查失败")
        guardrail_data = guardrail["data"]
        final_markdown = guardrail_data.get("rewritten_markdown") or markdown
        if not guardrail_data.get("passed"):
            rewrite = self.registry.call("rewrite_report_violations", {"markdown": final_markdown}, task_id=task.task_id).to_dict()
            if rewrite.get("success"):
                final_markdown = rewrite["data"]["markdown"]
                guardrail_data = {**guardrail_data, "rewritten_markdown": final_markdown}

        saved = self.registry.call(
            "save_report",
            {
                "task_id": task.task_id,
                "portfolio_id": portfolio.portfolio_id,
                "markdown": final_markdown,
                "guardrail": guardrail_data,
            },
            task_id=task.task_id,
        ).to_dict()
        if not saved.get("success"):
            raise RuntimeError(saved.get("error_message") or "报告保存失败")

        summary = f"报告已生成并归档，report_id={saved['data']['report_id']}，安全审查通过={saved['data']['passed_guardrail']}。"
        self._record(
            task.task_id,
            thought="报告生成完成，归档前已完成规则安全审查和模型审查补充。",
            action="report_summary",
            observation=summary,
        )
        return {
            "summary": summary,
            "report_id": saved["data"]["report_id"],
            "passed_guardrail": saved["data"]["passed_guardrail"],
            "sections": sections,
        }

    def _collect_sections(self, task: AnalysisTask, portfolio: Portfolio) -> dict[str, Any]:
        sections: dict[str, Any] = {}
        day6 = task.metadata.get("day6_result", {})
        finance = day6.get("finance", {}).get("data") if isinstance(day6, dict) else None
        if not finance:
            finance = FinanceAgent(self.registry, self.uow).run(task.task_id, portfolio)
        sections["finance"] = finance

        announcement = task.metadata.get("day7_result")
        if not announcement:
            announcement = AnnouncementAgent(self.registry, self.uow).run(task.task_id, portfolio)
        sections["announcement"] = announcement

        review = task.metadata.get("day8_result")
        if not review:
            review = ReviewAgent(self.registry, self.uow).run(task.task_id, portfolio)
        sections["review"] = review
        return sections

    def _record(self, task_id: str, thought: str, action: str, observation: str) -> AgentRunRecord:
        return self.uow.agent_runs.save(
            AgentRunRecord(
                task_id=task_id,
                agent_name=self.name,
                thought=thought,
                action=action,
                observation=observation[:1000],
            )
        )
