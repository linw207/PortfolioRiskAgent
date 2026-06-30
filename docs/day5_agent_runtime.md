# Day5 Agent Runtime

## Scope

Day5 implements the shared Agent execution foundation only. It does not implement OrchestratorAgent, FinanceAgent, AnnouncementAgent, ReviewAgent, or ReportAgent business logic.

## Components

- `src/infra/external/ollama_client.py`
  - `/api/tags` model health check.
  - OpenAI-compatible `/v1/chat/completions` chat call.
  - Native `/api/generate` fallback.
- `src/app/service/agent_runtime/base_agent.py`
  - Base ReAct loop.
  - JSON Action parsing.
  - Tool whitelist enforcement.
  - Tool retry for transient tool failures.
  - Agent run trace persistence.
  - Max step boundary.
- `src/app/service/agent_runtime/context.py`
  - Context truncation while preserving head and tail.
- `src/app/service/agent_runtime_service.py`
  - Factory for configured BaseAgent instances.
- `src/api/web/controller/model_controller.py`
  - `GET /model/health`.

## JSON Action Contract

Every model step must output:

```json
{
  "思考": "...",
  "动作": "tool_name or final_answer",
  "参数": {}
}
```

Invalid JSON Action stops the current Agent run and records a trace.

## Runtime Boundaries

- Default `MAX_AGENT_STEPS=6`.
- Default `MAX_CONTEXT_CHARS=12000`.
- Default `TOOL_RETRY_TIMES=1`.
- Tool calls are made through the MCP-style registry only.
- Tool name must be in the Agent's allowed tool list.
- Investment advice, target prices, return promises, and price predictions remain prohibited in prompts.

## Local Ollama Verification

Local `.env` currently points to:

- `OLLAMA_BASE_URL=http://192.168.2.43:11434`
- `OLLAMA_MODEL=qwen3.5:4b`
- `MODEL_TIMEOUT_SECONDS=60`

Smoke result on 2026-06-25:

- `/api/tags` available.
- `/api/generate` returned a valid JSON Action.
- `BaseAgent` + Ollama returned `final_answer=ok` in one step.
