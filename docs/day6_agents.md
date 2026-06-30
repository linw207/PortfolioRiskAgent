# Day6 OrchestratorAgent And FinanceAgent

## Scope

Day6 completes the first Agent execution chain:

```text
AnalysisTask -> OrchestratorAgent -> run_finance_agent tool -> FinanceAgent -> financial MCP tools
```

It intentionally does not implement AnnouncementAgent RAG, ReviewAgent, ReportAgent, notifications, or report safety review.

## Components

- `src/app/service/agents/orchestrator_agent.py`
  - Records Orchestrator thought/action/observation.
  - Registers `run_finance_agent` as an internal MCP-style tool.
  - Calls FinanceAgent through the registry, so professional agents are tool-like from the orchestrator perspective.
- `src/app/service/agents/finance_agent.py`
  - Calls deterministic tools:
    - `calculate_portfolio_risk`
    - `get_stock_price`
    - `get_financial_metrics`
  - Records FinanceAgent trace.
  - Produces a finance summary and structured risk payload.
- `src/app/service/task_service.py`
  - Adds `run_finance_check`.
  - Updates task status from `pending` to `running` to `completed`/`failed`.
  - Stores Day6 result in `AnalysisTask.metadata["day6_result"]`.
- `src/api/web/controller/task_controller.py`
  - Adds `POST /tasks/{task_id}/run-finance-check`.

## Runtime Notes

- The first Day6 implementation uses deterministic orchestration for stability while preserving the intended Agent boundary.
- Day7 can extend the orchestrator decision logic to call AnnouncementAgent when FinanceAgent identifies concentration, loss, or volatility flags.
- Every tool call is still audited through `tool_call_records`.
