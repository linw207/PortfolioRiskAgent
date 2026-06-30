from __future__ import annotations

import re
from typing import Any

from src.domain.entity import Portfolio, ReportArchive
from src.domain.time import now_iso
from src.infra.external.ollama_client import OllamaClient
from src.infra.repo.mem import MemUnitOfWork


FORBIDDEN_PATTERNS: dict[str, str] = {
    r"建议买入": "不提供买入建议",
    r"建议卖出": "不提供卖出建议",
    r"强烈推荐": "不提供推荐评级",
    r"目标价[：:\s]*\d+(\.\d+)?": "不提供目标价",
    r"保证收益": "不承诺收益",
    r"稳赚": "不承诺收益",
    r"必涨": "不承诺价格方向",
}


class ReportService:
    def __init__(self, uow: MemUnitOfWork, ollama: OllamaClient | None = None) -> None:
        self.uow = uow
        self.ollama = ollama

    def render_report(self, portfolio: Portfolio, sections: dict[str, Any]) -> str:
        finance = sections.get("finance", {})
        announcement = sections.get("announcement", {})
        review = sections.get("review", {})
        generated_at = now_iso()
        lines = [
            f"# {portfolio.name} 持仓风险体检报告",
            "",
            f"- 生成时间：{generated_at}",
            f"- 用户 ID：{portfolio.user_id}",
            f"- 组合 ID：{portfolio.portfolio_id}",
            "- 合规声明：本报告仅用于风险提示和人工复核，不构成投资建议、收益承诺或交易指令。",
            "",
            "## 一、持仓概览",
            "",
            "| 股票代码 | 名称 | 持仓数量 | 成本价 |",
            "| --- | --- | ---: | ---: |",
        ]
        for holding in portfolio.holdings:
            lines.append(f"| {holding.symbol} | {holding.name or '-'} | {holding.shares} | {holding.cost_price} |")
        lines.extend(["", "## 二、金融风险摘要", "", _section_summary(finance, "暂无金融分析结果。")])
        finance_flags = finance.get("risk", {}).get("data", {}).get("risk_flags", []) if isinstance(finance, dict) else []
        if finance_flags:
            lines.extend(["", "### 金融风险标记", ""])
            for flag in finance_flags:
                lines.append(f"- {flag}")
        lines.extend(["", "## 三、公告风险事件", ""])
        announcement_events = announcement.get("risk_events", []) if isinstance(announcement, dict) else []
        if announcement_events:
            for event in announcement_events:
                evidence = event.get("evidence", {})
                lines.extend(
                    [
                        f"- {event.get('symbol', '')}：{event.get('risk_label', '')}（{event.get('severity', '')}）",
                        f"  - 证据：{evidence.get('title', '')}",
                        f"  - 来源：{evidence.get('source', '')} {evidence.get('url', '')}",
                    ]
                )
        else:
            lines.append("未识别到命中预设风险关键词的公告事件。")
        lines.extend(["", "## 四、交易复盘与待人工复核问题", ""])
        questions = review.get("questions", []) if isinstance(review, dict) else []
        if questions:
            for question in questions:
                lines.append(f"- {question}")
        else:
            lines.append("暂无待人工复核问题。")
        lines.extend(
            [
                "",
                "## 五、数据来源与审计",
                "",
                "- 行情与财务：AKShare 或本地样例降级数据，工具调用记录已写入 ToolCallRecord。",
                "- 公告证据：公告 RAG 工具检索，证据包含标题、来源和 URL。",
                "- 交易复盘：用户交易日志、公告风险事件、历史 agent memory。",
                "- 安全审查：规则审查优先，模型审查作为补充。",
            ]
        )
        return "\n".join(lines).strip() + "\n"

    def guardrail_check(self, markdown: str, use_model: bool = True) -> dict[str, Any]:
        violations = []
        rewritten = markdown
        for pattern, replacement in FORBIDDEN_PATTERNS.items():
            if re.search(pattern, rewritten):
                violations.append({"pattern": pattern, "replacement": replacement})
                rewritten = re.sub(pattern, replacement, rewritten)
        model_review = self._model_guardrail_check(rewritten) if use_model else {"available": False, "reason": "disabled"}
        passed = not violations and not model_review.get("blocked", False)
        return {
            "passed": passed,
            "violations": violations,
            "rewritten_markdown": rewritten,
            "model_review": model_review,
        }

    def save_report(self, task_id: str, portfolio_id: str, markdown: str, guardrail: dict[str, Any]) -> ReportArchive:
        report = ReportArchive(
            task_id=task_id,
            portfolio_id=portfolio_id,
            markdown=guardrail.get("rewritten_markdown") or markdown,
            passed_guardrail=bool(guardrail.get("passed")),
            metadata={
                "guardrail": guardrail,
                "generated_by": "ReportAgent",
            },
        )
        return self.uow.reports.save(report)

    def get_report_by_task(self, task_id: str) -> ReportArchive | None:
        return self.uow.reports.get_by_task(task_id)

    def _model_guardrail_check(self, markdown: str) -> dict[str, Any]:
        if self.ollama is None:
            return {"available": False, "reason": "ollama_not_configured"}
        prompt = (
            "你是金融报告安全审查器。只检查文本是否包含买卖建议、目标价、收益承诺或诱导交易。"
            "请只返回 JSON：{\"blocked\": false, \"reason\": \"...\"}。\n\n"
            f"文本：\n{markdown[:6000]}"
        )
        try:
            response = self.ollama.generate(prompt, think=False, num_predict=256)
        except Exception as exc:  # noqa: BLE001
            return {"available": False, "reason": str(exc)}
        blocked = any(word in response for word in ["true", "违规", "买卖建议", "目标价", "收益承诺"])
        return {"available": True, "blocked": blocked, "raw": response[:1000]}


def _section_summary(section: dict[str, Any], default: str) -> str:
    if not isinstance(section, dict):
        return default
    if section.get("summary"):
        return str(section["summary"])
    if section.get("data", {}).get("summary"):
        return str(section["data"]["summary"])
    return default
