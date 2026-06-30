# Day1-2 Storage Design

## MongoDB Collections

- `users`: user profile and risk preference.
- `portfolios`: portfolio aggregate root, embeds current holding snapshot for Day1-2.
- `watch_items`: watch pool items and alert switches.
- `trade_journals`: user-entered buy/add/reduce/sell events.
- `analysis_tasks`: task status, progress and recovery metadata.
- `agent_run_records`: ReAct/Reflection trace records, one document per step.
- `tool_call_records`: MCP-style tool invocation audit log.
- `report_archives`: generated Markdown report and guardrail metadata.
- `notification_channels`: Feishu/WeCom webhook configuration.
- `notification_records`: notification send result and retry state.
- `scheduled_jobs`: daily/weekly/radar/reminder schedule definitions.

## Repository Implementation

MongoDB repository implementation lives in:

- `src/infra/repo/mongo/client.py`
- `src/infra/repo/mongo/decoder.py`
- `src/infra/repo/mongo/unit_of_work.py`

Runtime switch:

- `USE_MEMORY_FALLBACK=true`: use in-memory repositories for unit tests and offline development.
- `USE_MEMORY_FALLBACK=false`: use real MongoDB repositories.

Smoke command:

```bash
python3 scripts/mongo_repo_smoke.py
```

If using the project virtualenv created during local setup:

```bash
.venv/bin/python -B scripts/mongo_repo_smoke.py
```

## Initial Index Plan

- `portfolios`: `user_id`, `created_at`.
- `watch_items`: unique compound index on `user_id + symbol`.
- `trade_journals`: `user_id + symbol + trade_date`.
- `analysis_tasks`: `user_id + status + created_at`, `portfolio_id`.
- `agent_run_records`: `task_id + created_at`.
- `tool_call_records`: `task_id + tool_name + created_at`.
- `report_archives`: `task_id`, `portfolio_id + created_at`.
- `notification_records`: `channel_id + event_type + created_at`.
- `scheduled_jobs`: `user_id + job_type + enabled`.

## Redis Key Design

- `pra:task:{task_id}:status`: task progress snapshot for polling.
- `pra:queue:analysis`: lightweight analysis task queue for Day10 replacement.
- `pra:queue:notification`: notification send queue.
- `pra:cache:quote:{symbol}`: quote cache.
- `pra:lock:schedule:{job_type}:{target_id}`: prevents duplicate scheduled task creation.

Implemented Redis runtime code:

- `src/app/service/redis_runtime_service.py`
- `src/infra/repo/redis/client.py`
- task creation writes `pra:task:{task_id}:status`
- task creation pushes `task_id` into `pra:queue:analysis`
- Day6 task execution refreshes `pra:task:{task_id}:status`
- schedule lock helpers are available through Redis `SET NX EX`

## Vector Store Design

Provider: Chroma by default.

- `announcement_chunks` / `announcement_chunks_qwen3`: announcement chunks with metadata `{symbol,title,published_at,source,url,risk_keywords}`.
- `agent_memory` / `agent_memory_qwen3`: historical risk event summaries and report summaries with metadata `{user_id,symbol,task_id,created_at}`.

Day7 has implemented minimal announcement RAG ingestion and retrieval. Day8 uses the memory collection for trade review/reflection summaries.

Implemented Chroma runtime code:

- `src/app/service/vector_memory_service.py`
- `src/infra/repo/vector/client.py`
- `POST /infra/vector/announcements/upsert`
- `POST /infra/vector/announcements/search`
- `POST /infra/vector/memory/upsert`
- `POST /infra/vector/memory/search`

The vector service now uses Ollama `qwen3-embedding:4b` first through `OllamaClient.embed`. Deterministic local embedding remains available for unit tests and can be enabled explicitly with `VECTOR_ALLOW_EMBEDDING_FALLBACK=true`; the default is false to avoid polluting semantic collections with the wrong vector dimension.

## Local Initialization Status

Initialized on 2026-06-25:

- MongoDB Homebrew service: `mongodb-community@7.0`
- Mongo database: `portfolio_risk_agent`
- Redis Docker container: `pra-redis`, host port `6379`
- Chroma Docker container: `pra-chroma`, host port `8001`, container port `8000`
- Chroma collections:
  - `announcement_chunks`
  - `agent_memory`

Useful commands:

```bash
brew services start mongodb-community@7.0
docker compose up -d redis chroma
mongosh --quiet scripts/init_mongo.js
python3 scripts/init_chroma.py
bash scripts/init_redis.sh
python3 scripts/check_datastores.py
```

Redis + Chroma smoke:

```bash
python3 scripts/redis_chroma_smoke.py
```

## Day3-4 Tool Audit Records

`tool_call_records` stores every MCP-style tool call:

- `task_id`: empty for manual/debug calls, task id for Agent calls.
- `tool_name`: registered tool name.
- `arguments`: raw validated arguments.
- `success`: call result.
- `source`: `AKShare`, `local_sample`, `risk_calculator`, etc.
- `error_code` / `error_message`: normalized failure reason.
- `result_summary`: truncated result preview for evaluation and debugging.
