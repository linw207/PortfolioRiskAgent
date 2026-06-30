from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from src.app.service.agent_runtime.base_agent import BaseAgent
from src.app.service.announcement_rag_service import RISK_TAXONOMY
from src.app.service.notification_service import NotificationService
from src.app.service.portfolio_service import PortfolioService
from src.app.service.report_archive_service import ReportArchiveService
from src.app.service.report_service import ReportService
from src.app.service.task_service import TaskService
from src.app.service.trade_journal_service import TradeJournalService
from src.domain.entity import AnalysisTask, TaskStatus
from src.infra.adapter.mcp import MCPToolRegistry
from src.infra.external.market_data_gateway import MarketDataGateway
from src.infra.repo.mem import MemUnitOfWork


class EvaluationService:
    """Small reproducible benchmark suite for Day13.

    The implementation follows the evaluation split from HelloAgents chapter 12:
    BFCL-style structural matching for tool calls, GAIA-style task completion
    checks for end-to-end cases, and deterministic judge checks for guardrails.
    """

    def __init__(
        self,
        uow: MemUnitOfWork,
        registry: MCPToolRegistry,
        task_service: TaskService,
        report_archive_service: ReportArchiveService,
        report_service: ReportService,
        notification_service: NotificationService,
        dataset_dir: Path | None = None,
    ) -> None:
        self.uow = uow
        self.registry = registry
        self.task_service = task_service
        self.report_archive_service = report_archive_service
        self.report_service = report_service
        self.notification_service = notification_service
        self.dataset_dir = dataset_dir or Path(__file__).resolve().parents[4] / "data" / "evaluation"
        self._last_result: dict[str, Any] | None = None

    def run_all(self) -> dict[str, Any]:
        started = time.perf_counter()
        suites = {
            "tool_call": self.evaluate_tool_calls(),
            "announcement_risk": self.evaluate_announcement_risk(),
            "guardrail": self.evaluate_guardrail(),
            "end_to_end": self.evaluate_end_to_end(),
            "stability": self.evaluate_stability(),
        }
        result = {
            "methodology": {
                "tool_call": "BFCL-inspired structural matching: tool name exact match and recursive argument normalization.",
                "announcement_risk": "Domain classification metrics: precision, recall, F1, and exact case accuracy.",
                "guardrail": "Deterministic judge for unsafe financial-report phrases: interception rate and false positive rate.",
                "end_to_end": "GAIA-inspired task completion check with normalized section and notification expectations.",
                "stability": "Failure-recovery checks for model outage, data-source fallback, notification failure, and max-step stop.",
            },
            "summary": {
                "tool_call_accuracy": suites["tool_call"]["metrics"]["overall_accuracy"],
                "risk_identification_f1": suites["announcement_risk"]["metrics"]["f1"],
                "guardrail_interception_rate": suites["guardrail"]["metrics"]["interception_rate"],
                "end_to_end_completion_rate": suites["end_to_end"]["metrics"]["completion_rate"],
                "stability_pass_rate": suites["stability"]["metrics"]["pass_rate"],
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            },
            "suites": suites,
        }
        self._last_result = result
        return result

    def latest(self) -> dict[str, Any] | None:
        return self._last_result

    def evaluate_tool_calls(self) -> dict[str, Any]:
        cases = self._load_cases("tool_call_cases.json")
        details = []
        category_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})
        for case in cases:
            predicted = self._predict_tool_calls(case)
            expected = case["expected_calls"]
            correct = _calls_match(predicted, expected)
            category = case.get("category", "unknown")
            category_stats[category]["total"] += 1
            category_stats[category]["correct"] += int(correct)
            details.append(
                {
                    "id": case["id"],
                    "category": category,
                    "prompt": case["prompt"],
                    "expected_calls": expected,
                    "predicted_calls": predicted,
                    "correct": correct,
                }
            )
        total = len(cases)
        correct_count = sum(1 for item in details if item["correct"])
        return {
            "name": "tool_call",
            "case_count": total,
            "metrics": {
                "overall_accuracy": _safe_ratio(correct_count, total),
                "category_accuracy": {
                    category: _safe_ratio(stats["correct"], stats["total"])
                    for category, stats in sorted(category_stats.items())
                },
                "error_rate": 1 - _safe_ratio(correct_count, total),
            },
            "details": details,
        }

    def evaluate_announcement_risk(self) -> dict[str, Any]:
        cases = self._load_cases("announcement_risk_cases.json")
        details = []
        true_positive = false_positive = false_negative = 0
        exact_correct = 0
        for case in cases:
            predicted = self._classify_announcement_risks(f"{case['title']}\n{case['content']}")
            expected = sorted(set(case["expected_risk_types"]))
            predicted_set = set(predicted)
            expected_set = set(expected)
            true_positive += len(predicted_set & expected_set)
            false_positive += len(predicted_set - expected_set)
            false_negative += len(expected_set - predicted_set)
            exact = predicted_set == expected_set
            exact_correct += int(exact)
            details.append(
                {
                    "id": case["id"],
                    "symbol": case["symbol"],
                    "title": case["title"],
                    "expected_risk_types": expected,
                    "predicted_risk_types": predicted,
                    "correct": exact,
                }
            )
        precision = _safe_ratio(true_positive, true_positive + false_positive)
        recall = _safe_ratio(true_positive, true_positive + false_negative)
        f1 = _safe_ratio(2 * precision * recall, precision + recall)
        return {
            "name": "announcement_risk",
            "case_count": len(cases),
            "metrics": {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "exact_case_accuracy": _safe_ratio(exact_correct, len(cases)),
                "true_positive": true_positive,
                "false_positive": false_positive,
                "false_negative": false_negative,
            },
            "details": details,
        }

    def evaluate_guardrail(self) -> dict[str, Any]:
        cases = self._load_cases("guardrail_cases.json")
        details = []
        unsafe_total = unsafe_blocked = safe_total = safe_blocked = correct = 0
        for case in cases:
            result = self.report_service.guardrail_check(case["text"], use_model=False)
            blocked = not result["passed"] or bool(result["violations"])
            expected_blocked = bool(case["expected_blocked"])
            if expected_blocked:
                unsafe_total += 1
                unsafe_blocked += int(blocked)
            else:
                safe_total += 1
                safe_blocked += int(blocked)
            replacements_found = [
                replacement
                for replacement in case.get("expected_replacements", [])
                if replacement in result["rewritten_markdown"]
            ]
            is_correct = blocked == expected_blocked and len(replacements_found) == len(case.get("expected_replacements", []))
            correct += int(is_correct)
            details.append(
                {
                    "id": case["id"],
                    "expected_blocked": expected_blocked,
                    "predicted_blocked": blocked,
                    "expected_replacements": case.get("expected_replacements", []),
                    "replacements_found": replacements_found,
                    "correct": is_correct,
                }
            )
        return {
            "name": "guardrail",
            "case_count": len(cases),
            "metrics": {
                "overall_accuracy": _safe_ratio(correct, len(cases)),
                "interception_rate": _safe_ratio(unsafe_blocked, unsafe_total),
                "false_positive_rate": _safe_ratio(safe_blocked, safe_total),
            },
            "details": details,
        }

    def evaluate_end_to_end(self) -> dict[str, Any]:
        cases = self._load_cases("e2e_cases.json")
        details = []
        completed = 0
        for case in cases:
            started = time.perf_counter()
            user_id = case["user_id"]
            portfolio = PortfolioService(self.uow).create_portfolio(
                user_id=user_id,
                name=case["portfolio"]["name"],
                holdings_payload=case["portfolio"]["holdings"],
            )
            TradeJournalService(self.uow).add_journal(user_id, case["journal"])
            self.notification_service.create_channel(
                user_id,
                {
                    "channel_type": "feishu",
                    "channel_name": "eval-mock",
                    "webhook_url": "mock://evaluation",
                    "event_types": [case["expected_event_type"], "task_failed"],
                },
            )
            task = self.task_service.create_task(user_id, portfolio.portfolio_id)
            task.metadata.update(_stable_report_sections())
            self.uow.analysis_tasks.save(task)
            finished = self.task_service.run_report_check(task.task_id, notify=True)
            report = self.report_archive_service.get_by_task(task.task_id)
            records = self.notification_service.list_records(user_id)
            has_report = report is not None
            section_hits = [section for section in case["expected_report_sections"] if report and section in report.markdown]
            has_notification = any(record.event_type == case["expected_event_type"] and record.status == "sent" for record in records)
            success = finished.status == TaskStatus.COMPLETED and has_report and has_notification and len(section_hits) == len(case["expected_report_sections"])
            completed += int(success)
            details.append(
                {
                    "id": case["id"],
                    "task_id": task.task_id,
                    "status": finished.status,
                    "has_report": has_report,
                    "section_hits": section_hits,
                    "has_notification": has_notification,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    "correct": success,
                }
            )
        return {
            "name": "end_to_end",
            "case_count": len(cases),
            "metrics": {
                "completion_rate": _safe_ratio(completed, len(cases)),
                "avg_latency_ms": round(sum(item["latency_ms"] for item in details) / max(len(details), 1), 2),
            },
            "details": details,
        }

    def evaluate_stability(self) -> dict[str, Any]:
        checks = [
            self._check_model_unavailable(),
            self._check_data_source_fallback(),
            self._check_notification_failure(),
            self._check_agent_max_steps(),
        ]
        passed = sum(1 for item in checks if item["passed"])
        return {
            "name": "stability",
            "case_count": len(checks),
            "metrics": {
                "pass_rate": _safe_ratio(passed, len(checks)),
                "passed": passed,
                "failed": len(checks) - passed,
            },
            "details": checks,
        }

    def _load_cases(self, filename: str) -> list[dict[str, Any]]:
        with (self.dataset_dir / filename).open("r", encoding="utf-8") as file:
            return json.load(file)

    def _predict_tool_calls(self, case: dict[str, Any]) -> list[dict[str, Any]]:
        prompt = case["prompt"]
        context = case.get("context", {})
        if "不需要" in prompt or "无需" in prompt:
            return []
        if "价格" in prompt or "最新股票" in prompt:
            return [{"name": "get_stock_price", "arguments": {"symbol": _extract_symbol(prompt)}}]
        if "财务" in prompt:
            return [{"name": "get_financial_metrics", "arguments": {"symbol": _extract_symbol(prompt)}}]
        if "组合" in prompt and "风险" in prompt:
            portfolio = context.get("portfolio", {})
            return [{"name": "calculate_portfolio_risk", "arguments": {"portfolio_id": portfolio.get("portfolio_id", "")}}]
        return []

    def _classify_announcement_risks(self, text: str) -> list[str]:
        matched = []
        for risk_type, config in RISK_TAXONOMY.items():
            if any(keyword in text for keyword in config["keywords"]):
                matched.append(risk_type)
        return sorted(set(matched))

    def _check_model_unavailable(self) -> dict[str, Any]:
        class FailingOllama:
            def generate(self, prompt: str) -> str:
                raise RuntimeError("model unavailable")

        service = ReportService(MemUnitOfWork(), ollama=FailingOllama())
        result = service.guardrail_check("本报告仅提示风险，不构成投资建议。", use_model=True)
        return {
            "id": "stability_model_unavailable",
            "passed": result["passed"] and result["model_review"]["available"] is False,
            "observation": result["model_review"],
        }

    def _check_data_source_fallback(self) -> dict[str, Any]:
        class FailingAKShare:
            def get_stock_quote(self, symbol: str) -> dict[str, Any]:
                raise RuntimeError("akshare unavailable")

        quote, source, degraded = MarketDataGateway(FailingAKShare()).stock_quote("300750.SZ")
        return {
            "id": "stability_data_source_unavailable",
            "passed": source == "local_sample" and degraded and quote.get("symbol") == "300750.SZ",
            "observation": {"source": source, "degraded": degraded, "symbol": quote.get("symbol")},
        }

    def _check_notification_failure(self) -> dict[str, Any]:
        class FailingFeishuBot:
            def send_text(self, webhook_url: str, title: str, content: str, secret: str = "") -> dict[str, Any]:
                raise RuntimeError("feishu unavailable")

        uow = MemUnitOfWork()
        service = NotificationService(uow, feishu_bot=FailingFeishuBot())
        service.create_channel(
            "eval_stability",
            {"channel_type": "feishu", "channel_name": "failing", "webhook_url": "https://example.invalid", "event_types": ["report_ready"]},
        )
        records = service.dispatch_event("eval_stability", "report_ready", "完成", "报告完成")
        return {
            "id": "stability_notification_failure",
            "passed": len(records) == 1 and records[0].status == "failed" and records[0].retry_count == 1,
            "observation": _public(records[0]),
        }

    def _check_agent_max_steps(self) -> dict[str, Any]:
        class LoopModel:
            def chat(self, messages: list[dict[str, str]]) -> str:
                return '{"思考":"继续查询","动作":"get_stock_price","参数":{"symbol":"300750.SZ"}}'

        uow = MemUnitOfWork()
        registry = MCPToolRegistry(uow)
        tool = self.registry.get("get_stock_price")
        if tool is not None:
            registry.register(tool)
        agent = BaseAgent("EvalAgent", "评估最大步数", LoopModel(), registry, uow, max_steps=2)
        result = agent.run("eval_max_steps", "持续调用工具直到达到上限", allowed_tools=["get_stock_price"])
        return {
            "id": "stability_agent_max_steps",
            "passed": result.stopped_reason == "max_steps_reached" and result.steps_used == 2,
            "observation": {"stopped_reason": result.stopped_reason, "steps_used": result.steps_used},
        }


def _stable_report_sections() -> dict[str, Any]:
    return {
        "day6_result": {
            "finance": {
                "data": {
                    "summary": "组合总市值 19680.00 元；总盈亏 -3820.00 元；第一大持仓占比 100.0%；风险标记 1 个。",
                    "risk": {"data": {"risk_flags": ["第一大持仓占比过高"]}},
                }
            }
        },
        "day7_result": {
            "summary": "检索到公告风险事件 1 条：股份质押 1 条。",
            "risk_events": [
                {
                    "symbol": "300750.SZ",
                    "risk_label": "股份质押",
                    "severity": "medium",
                    "evidence": {"title": "股份质押公告", "source": "evaluation", "url": "eval://pledge"},
                }
            ],
        },
        "day8_result": {
            "summary": "交易复盘生成待人工复核问题 1 个。",
            "questions": ["请人工复核 300750.SZ 的成长假设：当前财务增速出现压力。"],
        },
    }


def _calls_match(predicted: list[dict[str, Any]], expected: list[dict[str, Any]]) -> bool:
    if len(predicted) != len(expected):
        return False
    unmatched = [_normalize_call(call) for call in predicted]
    for expected_call in [_normalize_call(call) for call in expected]:
        if expected_call not in unmatched:
            return False
        unmatched.remove(expected_call)
    return not unmatched


def _normalize_call(call: dict[str, Any]) -> dict[str, Any]:
    return {"name": call.get("name", ""), "arguments": _normalize_value(call.get("arguments", {}))}


def _normalize_value(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, dict):
        return {str(key): _normalize_value(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, str):
        return value.strip().upper() if "." in value and any(char.isdigit() for char in value) else value.strip()
    return value


def _extract_symbol(text: str) -> str:
    for token in text.replace("，", " ").replace("。", " ").split():
        if "." in token and any(char.isdigit() for char in token):
            return token.strip()
    return ""


def _safe_ratio(numerator: float, denominator: float) -> float:
    return round(float(numerator) / float(denominator), 4) if denominator else 0.0


def _public(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    return value
