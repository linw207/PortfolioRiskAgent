# 简历项目描述

## 项目名称

PortfolioRiskAgent：主动型持仓风险监控与报告 Agent

## 一句话介绍

基于 DDD 后端、MCP 风格工具注册、RAG 证据检索和多 Agent 编排，实现从持仓导入、金融风险体检、公告风险识别、交易复盘、报告生成到飞书通知的端到端智能体应用。

## 可写入简历的描述

- 设计并实现生产级 DDD 后端结构，拆分 `api/app/domain/infra/factory` 分层，支持 MongoDB Repository、Redis 任务状态与锁、Chroma 向量检索和内存仓储降级。
- 构建 MCP 风格工具体系，统一工具 schema、白名单、参数校验、调用审计和 JSON Action fallback，接入行情、财务、公告检索、风险计算、RAG 证据检索和报告安全审查工具。
- 实现 Orchestrator、Finance、Announcement、Review、Report 多 Agent 协作链路，支持任务状态流转、AgentRun/ToolCall 轨迹归档和 Markdown 风险报告生成。
- 接入 Tavily/SerpAPI 混合搜索、Ollama 文本/Embedding、飞书 webhook/CLI 通知，完成定时任务、失败恢复和高风险事件通知。
- 参考 BFCL/GAIA/LLM Judge 思路建设评估体系，覆盖工具调用准确率、公告风险 F1、安全拦截率、端到端完成率、稳定性恢复和 GAIA validation 官方数据链路。
- 提供 FastAPI API、静态演示控制台、一键启动脚本和演示数据脚本，形成可复现的简历展示项目。

## 技术栈

- Python, FastAPI, Pydantic
- MongoDB, Redis, Chroma
- Ollama, Tavily, SerpAPI, AKShare
- DDD, Repository, UnitOfWork
- MCP-style Tool Registry, ReAct JSON Action
- GAIA/BFCL-inspired Evaluation

## 面试讲解主线

1. 为什么不是玩具 Agent：先讲 DDD 分层、仓储边界和基础设施真实接入。
2. Agent 如何可靠调用工具：讲工具 schema、白名单、调用记录、失败重试和 JSON Action。
3. 金融场景如何避免幻觉：讲公告 RAG、可信搜索域名、证据 URL、报告安全审查。
4. 如何工程化运行：讲 Redis 锁、定时任务、任务恢复、通知失败不影响主链路。
5. 如何证明有效：讲 Day13 评估体系和 GAIA 官方 validation 接入。

## 当前边界

- 当前金融数据以 AKShare 优先、本地样例降级，适合演示和开发验证。
- 公告风险识别以关键词 taxonomy + RAG 证据为主，模型化深度推理可继续增强。
- GAIA 已完成官方数据与 scoring 链路，但默认小模型未接入浏览/搜索工具，分数不是最终能力上限。

