# Day14 交付与演示说明

## 交付目标

Day14 将 PortfolioRiskAgent 从“功能已完成”整理为“可以演示、可以复现、可以写进简历”的交付状态：

- 一键启动本地开发服务。
- 一键生成演示数据和端到端报告。
- 提供 API 检查命令、前端演示路径和排障说明。
- 固化简历项目描述、技术亮点和讲解顺序。

## 一键启动

```bash
chmod +x scripts/start_dev.sh
./scripts/start_dev.sh
```

启动后打开：

```text
http://127.0.0.1:8000/app
```

脚本做的事情：

- 自动创建 `.venv`。
- 安装 `requirements.txt`。
- 执行 `compileall` 语法检查。
- 尝试运行 `scripts/check_datastores.py`，数据库不可用时不中断启动。
- 启动 FastAPI/uvicorn。

## 一键演示数据

```bash
.venv/bin/python -B scripts/day14_demo.py
```

脚本会创建：

- `user_demo` 的 Day14 演示组合。
- 一条交易日志。
- 一个 mock 飞书通知渠道。
- 一个每日持仓体检定时任务。
- 一个已完成的报告任务。
- 一条 `report_ready` 通知记录。

脚本输出包含 `portfolio_id`、`task_id`、`report_id`、`schedule_id` 和可复制的 `curl` 检查命令。

## 演示顺序

1. 打开 `/app`，展示总览页的健康状态。
2. 在“持仓上传”中展示样例组合，说明持仓是风控任务的输入边界。
3. 在“任务中心”选择演示组合，查看已完成任务。
4. 点击“报告”，展示 Markdown 风险体检报告和安全审查结果。
5. 点击“Agent 轨迹”，展示 `ReportAgent`、工具调用和审计链路。
6. 打开“通知设置”，展示 mock/飞书 CLI 渠道和通知记录。
7. 打开“定时任务”，说明 Redis 锁、任务恢复和 pending 不阻塞定时任务的修复。
8. 打开“评估面板”，展示 Day13 最小评估集和 GAIA validation 接入。

## 关键 API

```bash
curl http://127.0.0.1:8000/health
curl 'http://127.0.0.1:8000/portfolios?user_id=user_demo'
curl 'http://127.0.0.1:8000/tasks?user_id=user_demo'
curl 'http://127.0.0.1:8000/reports/tasks/<task_id>'
curl 'http://127.0.0.1:8000/tasks/<task_id>/agent-runs'
curl 'http://127.0.0.1:8000/tasks/<task_id>/tool-calls'
curl 'http://127.0.0.1:8000/notification-channels/records?user_id=user_demo'
curl -X POST 'http://127.0.0.1:8000/evaluations/run'
```

## 官方评测

GAIA validation 小样本：

```bash
.venv/bin/python -B scripts/official_benchmark_status.py \
  --gaia-eval \
  --gaia-config 2023_level1 \
  --gaia-split validation \
  --level 1 \
  --limit 1
```

当前边界：

- GAIA 工程链路已经稳定：数据下载、模型调用、答案抽取、exact-match scoring、结果落盘。
- 当前默认 `qwen3.5:4b` 小模型未接入搜索/浏览工具，GAIA 分数不代表完整 Agent 能力上限。
- BFCL 官方 CLI 可用，但 `qwen3.5:4b` 是 Ollama 标签，不是 BFCL registry key。`qwen3-4b` 需要 `QWEN_API_KEY`，`Qwen/Qwen3-4B` 需要本地 vLLM/SGLang 或兼容服务。

## 排障

- Redis/Chroma 不可达：确认 Docker Desktop 中 `pra-redis`、`pra-chroma` 已启动。
- Mongo 不可达：确认 Homebrew MongoDB 服务已启动，或使用 `USE_MEMORY_FALLBACK=true`。
- Ollama 超时：先用 `/api/generate` 单独测试模型；GAIA 使用 `GAIA_MODEL_TIMEOUT_SECONDS` 控制超时。
- 飞书 CLI 失败：先运行 `lark-cli auth status`，确认 `tokenStatus=valid` 且有 `im:message.send_as_user`。

