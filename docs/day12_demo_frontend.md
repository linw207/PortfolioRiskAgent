# Day12 Demo Frontend

## Scope

Day12 turns the backend workflow into a small operator console that can be opened directly from the FastAPI service.

Implemented pages:

- Overview: infrastructure health, model health, Feishu CLI status, and one-click demo run.
- Portfolio: create portfolios, upload CSV holdings, list holdings.
- Watchlist: add watched symbols and tags.
- Trade journal: create trade review inputs.
- Scheduler: create jobs, run enabled jobs, recover unfinished tasks.
- Notification: create Feishu webhook or Feishu CLI channels, inspect notification records, retry failed records.
- Tasks: create analysis tasks and trigger report generation.
- Report: load archived markdown reports for a task.
- Trace: view Agent run records and MCP-style tool call records.

## API additions

- `GET /app`: serves the demo console.
- `GET /static/app.css`: dashboard styling.
- `GET /static/app.js`: frontend workflow logic.
- `GET /tasks/{task_id}/agent-runs`: lists persisted Agent run traces for a task.
- `GET /tasks/{task_id}/tool-calls`: lists persisted tool call traces for a task.

## End-to-end path

The "运行端到端体检" button creates a demo portfolio and trade journal, creates a task, then calls `POST /tasks/{task_id}/run-report-check`.

The backend flow is:

1. ReportAgent orchestrates finance, announcement, and review checks.
2. Finance tools calculate deterministic portfolio risk.
3. AnnouncementAgent uses RAG evidence from Chroma/Ollama embedding when available.
4. ReviewAgent writes and retrieves Chroma memory.
5. ReportService applies guardrails and archives markdown output.
6. NotificationService can dispatch report/high-risk/task events to Feishu webhook or Feishu CLI channels.

## Notes

- Feishu CLI private message channels use `channel_type=feishu_cli`; the frontend stores the open id in the same backend `webhook_url` field because the domain entity has a generic endpoint field.
- The default open id in the demo page is the authorized user from the current local Feishu CLI setup.
- The page has no build step and no frontend package dependency; it is intentionally static to keep Day12 focused on end-to-end integration.
