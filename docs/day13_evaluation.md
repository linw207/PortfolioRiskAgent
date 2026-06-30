# Day13 Evaluation System

## Goal

Day13 adds a reproducible minimum evaluation suite for PortfolioRiskAgent. The design follows the evaluation split from HelloAgents Chapter 12:

- BFCL-style tool-call evaluation for function selection and argument filling.
- GAIA-style task completion evaluation for end-to-end workflows.
- Deterministic judge evaluation for financial-report guardrails.
- Domain classification metrics for announcement risk detection.
- Stability checks for expected failure modes.

## Datasets

Evaluation cases live under `data/evaluation/`:

- `tool_call_cases.json`: tool selection and argument construction cases.
- `announcement_risk_cases.json`: announcement title/content to risk taxonomy cases.
- `guardrail_cases.json`: unsafe/safe report text cases.
- `e2e_cases.json`: portfolio-to-report-to-notification cases.

## Metrics

- Tool call accuracy: BFCL-inspired exact tool name and recursive argument match.
- Announcement risk precision/recall/F1: compares predicted risk type set with expected risk type set.
- Guardrail interception rate: unsafe text blocked or rewritten divided by unsafe cases.
- Guardrail false positive rate: safe text incorrectly blocked divided by safe cases.
- End-to-end completion rate: task completed, report archived, expected sections present, notification sent.
- Stability pass rate: model outage, data fallback, notification failure, and max-step stop checks.

## Runtime

The evaluation service is available through:

- Python service: `create_container().evaluation_service.run_all()`
- CLI: `python3 -B scripts/run_evaluation.py`
- API: `POST /evaluations/run`
- API: `GET /evaluations/latest`
- Frontend: `/app` -> `评估面板`

## Latest Local Result

Last generated report:

- `data/evaluation/results/evaluation_20260627_150710.json`
- `data/evaluation/results/evaluation_report_20260627_150710.md`

Summary:

- Tool call accuracy: 100.0%
- Risk identification F1: 100.0%
- Guardrail interception rate: 100.0%
- End-to-end completion rate: 100.0%
- Stability pass rate: 100.0%

## Boundary

This is a minimum deterministic evaluation set, not a large public benchmark result. It proves the system has evaluation infrastructure, metrics, repeatable samples, result export, and UI display. Future work should expand case count, add adversarial announcements, add real LLM planner outputs, and track trend regressions in CI.

## Official Benchmarks

Official BFCL/GAIA integration has been added as an optional layer. See `docs/official_benchmarks.md`.

- `GET /evaluations/official/status`
- `GET /evaluations/official/gaia/sample?limit=5&level=1`
- `POST /evaluations/official/bfcl/status`
- `POST /evaluations/official/bfcl/generate`
- `POST /evaluations/official/bfcl/evaluate`
